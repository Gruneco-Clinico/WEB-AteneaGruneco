# -*- coding: utf-8 -*-
import json

from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from types import SimpleNamespace

from ..form_builder.schema import normalize_schema, validate_and_parse_post
from ..models import DatosDemograficos, Examen, ExamenSchemaVersion, ExamenSubmission, TipoVisita, Visita, VisitaExamen
from ..exam_legacy import LEGACY_REALIZAR_EXAMEN_IDS, examen_has_builder_schema, is_legacy_examen


def _staff(u):
    return u.is_authenticated and u.is_staff


def ensure_schema_version(examen: Examen, user) -> ExamenSchemaVersion:
    """Crea una nueva versión si el catálogo cambió respecto a la última publicada."""
    campos = examen.campos if isinstance(examen.campos, list) else []
    latest = (
        ExamenSchemaVersion.objects.filter(examen=examen).order_by("-version").first()
    )
    if latest:
        if json.dumps(latest.schema, sort_keys=True) == json.dumps(
            campos, sort_keys=True
        ):
            return latest
        ver = latest.version + 1
    else:
        ver = 1
    return ExamenSchemaVersion.objects.create(
        examen=examen,
        version=ver,
        schema=campos,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )


@login_required
def realizar_examen_builder(request, visita_id, examen_id, paciente_id):
    """GET: mostrar formulario dinámico. Requiere Examen.campos no vacío."""
    examen = get_object_or_404(Examen, pk=examen_id)
    if is_legacy_examen(examen_id):
        messages.error(
            request,
            "Este examen usa el flujo legacy y no puede abrirse con el Form Builder.",
        )
        return redirect("detalle_paciente", paciente_id=paciente_id)
    paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
    visita = get_object_or_404(Visita, id=visita_id, paciente=paciente)

    if visita.firmado:
        messages.error(request, "No se puede editar un examen de una visita firmada.")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    fields = normalize_schema(examen.campos)
    if not fields:
        messages.error(
            request,
            "Este examen no tiene campos configurados (Form Builder).",
        )
        return redirect("detalle_paciente", paciente_id=paciente_id)

    visita_examen_obj = get_object_or_404(
        VisitaExamen, visita_id=visita_id, examen_id=examen_id
    )

    datos_examen = {}
    datos_examen_json = "{}"
    modo_edicion = False
    try:
        submission = visita_examen_obj.builder_submission
    except ObjectDoesNotExist:
        submission = None
    if submission:
        datos_examen = dict(submission.answers)
        if submission.computed:
            datos_examen["_computed"] = submission.computed
        modo_edicion = True
        try:
            datos_examen_json = json.dumps(datos_examen, default=str)
        except TypeError:
            datos_examen_json = "{}"

    context = {
        "visita_examen": visita_id,
        "visita_examen_obj": visita_examen_obj,
        "paciente_id": paciente_id,
        "examen_id": examen_id,
        "examen": examen,
        "builder_fields": fields,
        "datos_examen": datos_examen,
        "datos_examen_json": datos_examen_json,
        "modo_edicion": modo_edicion,
        "paciente": paciente,
        "visita": visita,
    }
    return render(request, "examenes_builder/examen_generico.html", context)


@login_required
def guardar_examen_builder(request):
    if request.method != "POST":
        messages.error(request, "Método no permitido.")
        return redirect("index")

    visita_id = request.POST.get("visita_id")
    paciente_id = request.POST.get("paciente_id")
    examen_id = request.POST.get("examen_id")

    visita_examen = get_object_or_404(
        VisitaExamen, visita_id=visita_id, examen_id=examen_id
    )
    examen = visita_examen.examen
    visita = visita_examen.visita

    if is_legacy_examen(examen_id):
        messages.error(
            request,
            "No se pueden guardar respuestas del Form Builder en un examen legacy.",
        )
        return redirect("detalle_paciente", paciente_id=paciente_id)

    if visita.firmado:
        messages.error(request, "No se puede guardar: visita firmada.")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    if not examen_has_builder_schema(examen.campos):
        messages.error(
            request,
            "Este examen no tiene formulario dinámico configurado (campos vacíos).",
        )
        return redirect("detalle_paciente", paciente_id=paciente_id)

    answers, computed, errors = validate_and_parse_post(examen.campos, request.POST)
    if errors:
        for e in errors[:8]:
            messages.error(request, e)
        return redirect(
            "realizar_examen",
            visita_id=visita_id,
            examen_id=examen_id,
            paciente_id=paciente_id,
        )

    if visita_examen.estado == "pendiente":
        visita_examen.estado = "en_progreso"
        visita_examen.fecha_inicio = timezone.now()
        visita_examen.save(update_fields=["estado", "fecha_inicio"])

    sv = ensure_schema_version(examen, request.user)
    ExamenSubmission.objects.update_or_create(
        visita_examen=visita_examen,
        defaults={
            "answers": answers,
            "computed": computed,
            "schema_version": sv,
        },
    )

    visita_examen.estado = "completado"
    visita_examen.fecha_completado = timezone.now()
    visita_examen.save(update_fields=["estado", "fecha_completado"])

    messages.success(request, "Formulario guardado correctamente.")
    return redirect("detalle_paciente", paciente_id=paciente_id)


def _examen_assignments_by_tipo_visita():
    """{examen_id: [\"Tipo (Proyecto)\", ...]} desde TipoVisita.examenes (lista JSON)."""
    assign = {}
    for tv in TipoVisita.objects.select_related("proyecto").all():
        raw = tv.examenes
        if not isinstance(raw, list):
            continue
        label = f"{tv.nombre} ({tv.proyecto.nombre})"
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                eid = int(item.get("id"))
            except (TypeError, ValueError):
                continue
            assign.setdefault(eid, []).append(label)
    return assign


@login_required
@user_passes_test(_staff)
def exam_builder_list(request):
    assignments = _examen_assignments_by_tipo_visita()
    assigned_ids = set(assignments.keys())
    qs = Examen.objects.all()

    origen = (request.GET.get("origen") or "todos").strip().lower()
    if origen == "legacy":
        qs = qs.filter(pk__in=LEGACY_REALIZAR_EXAMEN_IDS)
    elif origen == "builder":
        qs = qs.exclude(pk__in=LEGACY_REALIZAR_EXAMEN_IDS)

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(nombre__icontains=q)

    categoria = (request.GET.get("categoria") or "").strip()
    valid_cats = {c[0] for c in Examen.CATEGORIA_CHOICES}
    if categoria in valid_cats:
        qs = qs.filter(categoria=categoria)

    asignacion = (request.GET.get("asignacion") or "todos").strip().lower()
    if asignacion == "asignado":
        if assigned_ids:
            qs = qs.filter(pk__in=assigned_ids)
        else:
            qs = qs.none()
    elif asignacion == "sin_asignar":
        if assigned_ids:
            qs = qs.exclude(pk__in=assigned_ids)

    orden = (request.GET.get("orden") or "id").strip().lower()
    if orden not in ("id", "nombre", "campos"):
        orden = "id"

    direccion = (request.GET.get("dir") or "desc").strip().lower()
    if direccion not in ("asc", "desc"):
        direccion = "desc"

    examenes_total = qs.count()

    if orden == "id":
        examenes = qs.order_by("-id" if direccion == "desc" else "id")
    elif orden == "nombre":
        if direccion == "desc":
            examenes = qs.order_by("-nombre", "-id")
        else:
            examenes = qs.order_by("nombre", "id")
    else:
        _items = list(qs)

        def _nodos(e):
            c = e.campos
            return len(c) if isinstance(c, list) else 0

        if direccion == "desc":
            _items.sort(key=lambda e: (-_nodos(e), -e.id))
        else:
            _items.sort(key=lambda e: (_nodos(e), e.id))
        examenes = _items

    return render(
        request,
        "examenes_builder/admin/lista_examenes.html",
        {
            "examenes": examenes,
            "assignments": assignments,
            "legacy_examen_ids": LEGACY_REALIZAR_EXAMEN_IDS,
            "filter_origen": origen if origen in ("todos", "legacy", "builder") else "todos",
            "filter_q": q,
            "filter_categoria": categoria if categoria in valid_cats else "",
            "filter_asignacion": (
                asignacion
                if asignacion in ("todos", "asignado", "sin_asignar")
                else "todos"
            ),
            "filter_orden": orden,
            "filter_dir": direccion,
            "categorias": Examen.CATEGORIA_CHOICES,
            "examenes_total": examenes_total,
        },
    )


@login_required
@user_passes_test(_staff)
def exam_builder_create(request):
    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        if not nombre:
            messages.error(request, "El nombre del examen es obligatorio.")
            return redirect("exam_builder_create")
        categoria = request.POST.get("categoria") or "OTROS"
        valid_cats = {c[0] for c in Examen.CATEGORIA_CHOICES}
        if categoria not in valid_cats:
            categoria = "OTROS"
        descripcion = request.POST.get("descripcion") or ""
        examen = Examen.objects.create(
            nombre=nombre,
            categoria=categoria,
            descripcion=descripcion,
            campos=[],
        )
        messages.success(
            request,
            "Examen creado. Agregue campos en el editor visual y guarde.",
        )
        return redirect("exam_builder_edit", pk=examen.pk)

    return render(
        request,
        "examenes_builder/admin/crear_examen.html",
        {
            "categorias": Examen.CATEGORIA_CHOICES,
        },
    )


@login_required
@user_passes_test(_staff)
def exam_builder_edit(request, pk):
    examen = get_object_or_404(Examen, pk=pk)
    if is_legacy_examen(pk):
        messages.warning(
            request,
            "Los exámenes legacy (plantillas en código) no se editan en el Form Builder.",
        )
        return redirect("exam_builder_list")
    if request.method == "POST":
        examen.nombre = request.POST.get("nombre", examen.nombre).strip()
        examen.descripcion = request.POST.get("descripcion", "")
        cat = request.POST.get("categoria") or examen.categoria
        valid_cats = {c[0] for c in Examen.CATEGORIA_CHOICES}
        if cat in valid_cats:
            examen.categoria = cat
        raw = request.POST.get("campos_json", "").strip()
        try:
            parsed = json.loads(raw) if raw else []
            if isinstance(parsed, dict) and "fields" in parsed:
                examen.campos = parsed["fields"]
            elif isinstance(parsed, list):
                examen.campos = parsed
            else:
                raise ValueError("campos debe ser lista o objeto con 'fields'")
        except (json.JSONDecodeError, ValueError) as exc:
            messages.error(request, f"JSON inválido: {exc}")
            return redirect("exam_builder_edit", pk=pk)
        examen.save()
        if request.POST.get("publicar"):
            ensure_schema_version(examen, request.user)
            messages.success(
                request,
                "Examen actualizado y versión de esquema publicada.",
            )
        else:
            messages.success(
                request,
                "Examen actualizado. Marque «Publicar al guardar» para fijar versión.",
            )
        return redirect("exam_builder_edit", pk=pk)

    campos_str = json.dumps(
        examen.campos if isinstance(examen.campos, list) else [],
        ensure_ascii=False,
        indent=2,
    )
    versions = examen.schema_versions.all()[:15]
    initial_fields = normalize_schema(examen.campos)
    return render(
        request,
        "examenes_builder/admin/editar_examen.html",
        {
            "examen": examen,
            "campos_str": campos_str,
            "versions": versions,
            "categorias": Examen.CATEGORIA_CHOICES,
            "initial_fields": initial_fields,
        },
    )


@login_required
@user_passes_test(_staff)
def exam_builder_preview(request):
    """POST: devuelve HTML del formulario dinámico (solo lectura) para vista previa."""
    if request.method != "POST":
        return HttpResponseForbidden()
    raw = request.POST.get("campos_json", "").strip()
    titulo = (request.POST.get("titulo_preview") or "Vista previa").strip()
    try:
        parsed = json.loads(raw) if raw else []
        if isinstance(parsed, dict) and "fields" in parsed:
            parsed = parsed["fields"]
        if not isinstance(parsed, list):
            raise ValueError("campos debe ser una lista")
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    fields = normalize_schema(parsed)
    examen = SimpleNamespace(id=0, nombre=titulo)
    html = render_to_string(
        "examenes_builder/preview_fragment.html",
        {
            "builder_fields": fields,
            "datos_examen": {},
            "examen": examen,
            "builder_preview_mode": True,
        },
        request=request,
    )
    return JsonResponse({"ok": True, "html": html})


@login_required
@user_passes_test(_staff)
def exam_builder_publish(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    examen = get_object_or_404(Examen, pk=pk)
    if is_legacy_examen(pk):
        messages.warning(
            request,
            "Los exámenes legacy no publican versión desde el Form Builder.",
        )
        return redirect("exam_builder_list")
    ensure_schema_version(examen, request.user)
    messages.success(request, "Versión de esquema publicada.")
    return redirect("exam_builder_edit", pk=pk)


@login_required
@user_passes_test(_staff)
def exam_builder_tipo_visita_edit(request, pk):
    tv = get_object_or_404(TipoVisita, pk=pk)
    if request.method == "POST":
        raw = request.POST.get("examenes_json", "").strip()
        try:
            tv.examenes = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            messages.error(request, f"JSON inválido: {exc}")
            return redirect("exam_builder_tipo_visita_edit", pk=pk)
        tv.save()
        messages.success(request, "Tipo de visita actualizado.")
        return redirect("exam_builder_tipo_visita_edit", pk=pk)

    examenes_str = json.dumps(
        tv.examenes if isinstance(tv.examenes, dict) else {},
        ensure_ascii=False,
        indent=2,
    )
    return render(
        request,
        "examenes_builder/admin/editar_tipo_visita.html",
        {
            "tipo_visita": tv,
            "examenes_str": examenes_str,
        },
    )


@login_required
def builder_result_response(request, visita_examen):
    """Si el examen es dinámico y hay submission, devuelve HttpResponse; si no, None."""
    if is_legacy_examen(visita_examen.examen_id):
        return None
    try:
        submission = visita_examen.builder_submission
    except ObjectDoesNotExist:
        return None
    fields = normalize_schema(visita_examen.examen.campos)
    return render(
        request,
        "examenes_builder/resultado_builder.html",
        {
            "visita_examen": visita_examen,
            "submission": submission,
            "builder_fields": fields,
            "paciente": visita_examen.visita.paciente,
        },
    )


@login_required
def ver_resultado_examen_builder(request, visita_examen_id):
    visita_examen = get_object_or_404(VisitaExamen, id=visita_examen_id)
    resp = builder_result_response(request, visita_examen)
    if resp is not None:
        return resp
    messages.error(request, "No hay resultado de formulario dinámico.")
    return redirect("detalle_paciente", paciente_id=visita_examen.visita.paciente_id)
