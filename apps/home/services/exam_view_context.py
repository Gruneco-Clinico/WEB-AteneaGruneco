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
                    "datos_resultado": submission.answers or {},
                    "puntaje_total": None,
                    "codigo_proyecto": None,
                },
            )
        raise ValueError("Sin resultado")

    datos_resultado = {}
    for field in resultado._meta.fields:
        if field.name != "visita_examen":
            datos_resultado[field.verbose_name or field.name] = getattr(
                resultado, field.name
            )

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
