# -*- encoding: utf-8 -*-
"""
Contexto compartido entre vista "Ver" y generación PDF (WeasyPrint).
"""
from apps.home.models import (
    SuenoAnamnesisResult,
    CognitivoAnamnesisResult,
    AnalisisGeneralResult,
    AntecedentesVisitaLink,
    AntecedentesResult,
    RevisionSistemasResult,
    DetalleRevisionSistemas,
    MedicamentosResult,
    SeguimientoIntervencionesResult,
    ProyectoPacienteExtra,
    ExamenSubmission,
)


# Valores crudos frecuentes en formularios legacy (sin choices en el modelo).
_VALORES_LEGIBLES = {
    "si": "Sí",
    "sí": "Sí",
    "no": "No",
    "ns": "No sabe",
    "nose": "No sabe",
    "no_sabe": "No sabe",
    "na": "No aplica",
    "n/a": "No aplica",
    "correcto": "Correcto",
    "incorrecto": "Incorrecto",
    "true": "Sí",
    "false": "No",
}


def _formatear_valor_campo(resultado, field):
    """Devuelve el valor legible de un campo de modelo (A-05).

    - Campos con ``choices`` → texto legible (``get_<field>_display``).
    - Booleanos → "Sí" (solo positivos; el negativo se omite).
    - Cadenas ``si``/``no``/``correcto``/… → forma capitalizada.
    - Resto → valor tal cual (fechas/base64 los formatea ``render_exam_value``).
    """
    valor = getattr(resultado, field.name, None)

    if getattr(field, "choices", None):
        metodo = getattr(resultado, f"get_{field.name}_display", None)
        if callable(metodo):
            display = metodo()
            if display not in (None, ""):
                return display

    from django.db.models import BooleanField

    if isinstance(field, BooleanField):
        # Solo se reporta el positivo ("Sí"); el negativo se omite para no
        # generar ruido. La semántica normal/anormal · presente/ausente se
        # aborda en la Épica B (examen físico/neurológico).
        return "Sí" if valor else ""

    if isinstance(valor, str):
        clave = valor.strip().lower()
        if clave in _VALORES_LEGIBLES:
            return _VALORES_LEGIBLES[clave]

    return valor


_CAMPOS_OMITIR_SECCIONES = frozenset(
    {"id", "visita_examen", "created_at", "updated_at",
     "fecha_creacion", "fecha_actualizacion"}
)


def _construir_secciones(resultado):
    """Agrupa los campos del resultado en subsecciones (A-06).

    Usa ``type(resultado).PRINT_SECCIONES_INICIOS`` (lista ordenada de
    ``(campo_inicial, título)``). Devuelve ``None`` si el modelo no lo define.
    Los campos no cubiertos por un marcador quedan en la subsección abierta más
    reciente, de modo que nunca se pierde información.
    """
    inicios = getattr(type(resultado), "PRINT_SECCIONES_INICIOS", None)
    if not inicios:
        return None

    inicio_map = dict(inicios)
    secciones = []
    actual = {"titulo": "General", "campos": []}

    for field in resultado._meta.fields:
        if field.name in _CAMPOS_OMITIR_SECCIONES:
            continue
        if field.name in inicio_map:
            if actual["campos"]:
                secciones.append(actual)
            actual = {"titulo": inicio_map[field.name], "campos": []}
        valor = _formatear_valor_campo(resultado, field)
        if valor in (None, ""):
            continue  # se omiten campos vacíos para no dejar filas/secciones huecas
        etiqueta = str(field.verbose_name) if field.verbose_name else field.name
        actual["campos"].append((etiqueta, valor))

    if actual["campos"]:
        secciones.append(actual)

    # Descarta subsecciones sin campos con contenido (evita títulos huérfanos).
    return [s for s in secciones if s["campos"]] or None


def _mapear_answers_a_etiquetas(visita_examen, answers):
    """Mapea las claves (id de campo) de un submission a sus etiquetas (A-05)."""
    try:
        from ..form_builder.schema import normalize_schema
    except Exception:
        return answers

    etiquetas = {}

    def _recorrer(nodos):
        for nodo in nodos:
            if not isinstance(nodo, dict):
                continue
            if nodo.get("type") == "section":
                _recorrer(normalize_schema(nodo.get("fields") or []))
                continue
            fid = nodo.get("id")
            if fid:
                etiquetas[fid] = nodo.get("label") or fid

    try:
        _recorrer(normalize_schema(getattr(visita_examen.examen, "campos", None)))
    except Exception:
        return answers

    return {etiquetas.get(k, k): v for k, v in answers.items()}


def get_context_ver_examen(visita_examen):
    """
    Devuelve (template_name, context) para renderizar resultado de un examen.
    Raises ValueError si no hay resultado o examen no completado.
    """
    if not visita_examen.esta_realizado:
        raise ValueError("Examen no completado")

    examen_id = visita_examen.examen_id
    paciente = visita_examen.visita.paciente

    if visita_examen.examen.nombre == "SeguimientoIntervencionesParticipantes_ANG":
        sesiones = SeguimientoIntervencionesResult.objects.filter(
            visita_examen=visita_examen
        ).order_by("numero_sesion")
        return (
            "examenes_resultados/resultado_seguimientointervenciones.html",
            {
                "visita_examen": visita_examen,
                "sesiones": sesiones,
                "paciente": paciente,
            },
        )

    resultado = visita_examen.get_resultado_instance()

    if examen_id == 10 and isinstance(resultado, SuenoAnamnesisResult):
        anamnesis = SuenoAnamnesisResult.objects.prefetch_related(
            "sustancias",
            "medicamentos",
            "pantallas",
            "actividades_en_cama",
            "actividades_fisicas",
            "sintomas_suenos",
            "sintomas_diurno",
            "tipos_queja_detalle",
        ).get(id=resultado.id)
        return (
            "examenes_resultados/resultado_sueno_anamnesis.html",
            {
                "visita_examen": visita_examen,
                "resultado": anamnesis,
                "paciente": paciente,
                "sustancias": anamnesis.sustancias.all(),
                "medicamentos": anamnesis.medicamentos.all(),
                "pantallas": anamnesis.pantallas.all(),
                "actividades_en_cama": anamnesis.actividades_en_cama.all(),
                "actividades_fisicas": anamnesis.actividades_fisicas.all(),
                "sintomas_suenos": anamnesis.sintomas_suenos.all(),
                "sintomas_diurnos": anamnesis.sintomas_diurno.all(),
                "tipos_queja": anamnesis.tipos_queja_detalle.all(),
            },
        )

    if examen_id == 20:
        cognitivo = visita_examen.cognitivo_anamnesis_resultado
        if not cognitivo:
            raise ValueError("Sin resultado cognitivo")
        cognitivo = CognitivoAnamnesisResult.objects.prefetch_related(
            "actitudes",
            "atenciones",
            "errores_lenguaje",
            "actividades_vida_diaria",
            "actividades_complejas",
        ).get(id=cognitivo.id)
        return (
            "examenes_resultados/resultado_cognitivo_Anamnesis.html",
            {
                "visita_examen": visita_examen,
                "resultado": cognitivo,
                "paciente": paciente,
                "actitudes": cognitivo.actitudes.all(),
                "atenciones": cognitivo.atenciones.all(),
                "errores_lenguaje": cognitivo.errores_lenguaje.all(),
                "actividades_vida_diaria": cognitivo.actividades_vida_diaria.all(),
                "actividades_complejas": cognitivo.actividades_complejas.all(),
            },
        )

    if examen_id == 7:
        analisis = AnalisisGeneralResult.objects.prefetch_related(
            "diagnosticos_cie10",
            "diagnosticos_dsmv",
            "diagnosticos_no_clasificados",
        ).get(visita_examen=visita_examen)
        return (
            "examenes_resultados/resultado_analisis_general.html",
            {
                "visita_examen": visita_examen,
                "resultado": analisis,
                "paciente": paciente,
                "diagnosticos_cie10": analisis.diagnosticos_cie10.all(),
                "diagnosticos_dsmv": analisis.diagnosticos_dsmv.all(),
                "diagnosticos_no_clasificados": analisis.diagnosticos_no_clasificados.all(),
            },
        )

    if examen_id == 5 or "antecedentes" in visita_examen.examen.nombre.lower():
        link = AntecedentesVisitaLink.objects.get(visita_examen=visita_examen)
        antecedentes = AntecedentesResult.objects.prefetch_related(
            "antecedentes_patologicos",
            "antecedentes_quirurgicos",
            "antecedentes_farmacologicos",
            "antecedentes_toxicos",
            "antecedentes_familiares",
            "antecedentes_alergicos",
            "antecedentes_traumaticos",
            "antecedentes_gineco",
            "antecedentes_epidemiologicos",
            "antecedentes_ets",
            "antecedentes_hospitalizaciones",
            "antecedentes_inmunizaciones",
            "antecedentes_transfusionales",
        ).get(id=link.antecedentes_result_id)
        return (
            "examenes_resultados/resultado_antecedentes.html",
            {
                "visita_examen": visita_examen,
                "resultado": antecedentes,
                "paciente": paciente,
                "patologicos": antecedentes.antecedentes_patologicos.all(),
                "quirurgicos": antecedentes.antecedentes_quirurgicos.all(),
                "farmacologicos": antecedentes.antecedentes_farmacologicos.all(),
                "toxicos": antecedentes.antecedentes_toxicos.all(),
                "familiares": antecedentes.antecedentes_familiares.all(),
                "alergicos": antecedentes.antecedentes_alergicos.all(),
                "traumaticos": antecedentes.antecedentes_traumaticos.all(),
                "gineco_obstetricos": getattr(antecedentes, "antecedentes_gineco", None),
                "epidemiologicos": antecedentes.antecedentes_epidemiologicos.all(),
                "ets": antecedentes.antecedentes_ets.all(),
                "hospitalizaciones": antecedentes.antecedentes_hospitalizaciones.all(),
                "inmunizaciones": antecedentes.antecedentes_inmunizaciones.all(),
                "transfusionales": antecedentes.antecedentes_transfusionales.all(),
            },
        )

    if examen_id == 4:
        revision = RevisionSistemasResult.objects.get(visita_examen=visita_examen)
        detalles = DetalleRevisionSistemas.objects.filter(
            revision_sistemas_result=revision
        ).order_by("sistema", "sintoma")
        sistemas_detalles = {}
        for detalle in detalles:
            sistemas_detalles.setdefault(detalle.sistema, []).append(detalle)
        return (
            "examenes_resultados/resultado_revision_sistemas.html",
            {
                "visita_examen": visita_examen,
                "resultado": revision,
                "paciente": paciente,
                "sistemas_detalles": sistemas_detalles,
            },
        )

    if examen_id == 8:
        medicamentos_result = MedicamentosResult.objects.get(
            visita_examen=visita_examen
        )
        return (
            "examenes_resultados/resultado_medicamentos.html",
            {
                "visita_examen": visita_examen,
                "resultado": medicamentos_result,
                "paciente": paciente,
                "medicamentos": medicamentos_result.medicamentos.all().order_by(
                    "nombre_comercial"
                ),
            },
        )

    if not resultado:
        submission = ExamenSubmission.objects.filter(
            visita_examen=visita_examen
        ).order_by("-id").first()
        if submission:
            return (
                "examenes_resultados/resultado_generico.html",
                {
                    "visita_examen": visita_examen,
                    "resultado": submission,
                    "paciente": paciente,
                    "datos_resultado": _mapear_answers_a_etiquetas(
                        visita_examen, submission.answers or {}
                    ),
                    "puntaje_total": None,
                    "codigo_proyecto": None,
                },
            )
        raise ValueError("Sin resultado")

    datos_resultado = {}
    for field in resultado._meta.fields:
        if field.name != "visita_examen":
            etiqueta = str(field.verbose_name) if field.verbose_name else field.name
            datos_resultado[etiqueta] = _formatear_valor_campo(resultado, field)

    proyecto = visita_examen.visita.Tipo_visita.proyecto
    codigo_proyecto = (
        ProyectoPacienteExtra.objects.filter(proyecto=proyecto, paciente=paciente)
        .values_list("codigo_proyecto", flat=True)
        .first()
    )
    puntaje_total = getattr(resultado, "puntaje_total", None) or getattr(
        resultado, "puntuacion_total", None
    )

    return (
        "examenes_resultados/resultado_generico.html",
        {
            "visita_examen": visita_examen,
            "resultado": resultado,
            "datos_resultado": datos_resultado,
            "secciones": _construir_secciones(resultado),
            "paciente": paciente,
            "codigo_proyecto": codigo_proyecto,
            "puntaje_total": puntaje_total,
        },
    )


# Mapeo examen_id → plantilla print (sin layout app)
PDF_EXAM_PRINT_TEMPLATES = {
    10: "pdf/examenes/sueno_anamnesis_print.html",
    7: "pdf/examenes/analisis_general_print.html",
    5: "pdf/examenes/antecedentes_print.html",
    20: "pdf/examenes/cognitivo_anamnesis_print.html",
    4: "pdf/examenes/revision_sistemas_print.html",
    8: "pdf/examenes/medicamentos_print.html",
    40: "pdf/examenes/seguimiento_intervenciones_print.html",
}


def get_print_template_for_examen(examen_id):
    return PDF_EXAM_PRINT_TEMPLATES.get(
        int(examen_id), "pdf/examenes/generico_print.html"
    )
