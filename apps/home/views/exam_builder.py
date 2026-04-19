# -*- coding: utf-8 -*-
import json

from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..form_builder.schema import normalize_schema, validate_and_parse_post
from ..models import DatosDemograficos, Examen, ExamenSchemaVersion, ExamenSubmission, TipoVisita, Visita, VisitaExamen
from ..exam_legacy import is_legacy_examen


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

    if visita.firmado:
        messages.error(request, "No se puede guardar: visita firmada.")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    if is_legacy_examen(examen_id):
        messages.error(request, "Este examen usa el flujo legacy, no el builder.")
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


@login_required
@user_passes_test(_staff)
def exam_builder_list(request):
    examenes = Examen.objects.all().order_by("nombre")
    return render(
        request,
        "examenes_builder/admin/lista_examenes.html",
        {"examenes": examenes},
    )


@login_required
@user_passes_test(_staff)
def exam_builder_edit(request, pk):
    examen = get_object_or_404(Examen, pk=pk)
    if request.method == "POST":
        examen.nombre = request.POST.get("nombre", examen.nombre).strip()
        examen.descripcion = request.POST.get("descripcion", "")
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
        messages.success(request, "Examen actualizado. Use Publicar para fijar versión.")
        return redirect("exam_builder_edit", pk=pk)

    campos_str = json.dumps(
        examen.campos if isinstance(examen.campos, list) else [],
        ensure_ascii=False,
        indent=2,
    )
    versions = examen.schema_versions.all()[:15]
    return render(
        request,
        "examenes_builder/admin/editar_examen.html",
        {
            "examen": examen,
            "campos_str": campos_str,
            "versions": versions,
        },
    )


@login_required
@user_passes_test(_staff)
def exam_builder_publish(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    examen = get_object_or_404(Examen, pk=pk)
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
