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
    """Devuelve el valor legible de un campo de modelo (A-05 / B-08).

    - Campos con ``choices`` → texto legible (``get_<field>_display``).
    - Booleanos con FIELD_TOGGLE_SEMANTICS → Detecta/Presente/Normal (True y False).
    - Booleanos genéricos → "Sí" (solo positivos; el negativo se omite).
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
        if _es_flag_seccion_evaluado(field.name):
            return ""  # metadato B-09; no se imprime como fila
        semantics = getattr(type(resultado), "FIELD_TOGGLE_SEMANTICS", None) or {}
        tipo = semantics.get(field.name)
        if tipo:
            from apps.home.models.field_toggle_semantics import formatear_toggle

            return formatear_toggle(tipo, bool(valor))
        # Genérico: solo positivo
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

# Banner/tabla: no mostrar "Puntaje total" (clínica: ítems bastan o confunde).
_OCULTAR_PUNTAJE_TOTAL = frozenset({
    "ParticipanteYesavageResult",
    "AQDCuidadorResult",
    "AQDParticipanteResult",
    "RedLatSpanishResult",  # ya tiene puntajes por componente
})

# Campos que no deben listarse como fila de parámetro (van en banner o sobran).
_CAMPOS_OCULTOS_POR_MODELO = {
    "ParticipanteYesavageResult": frozenset({"puntaje_total"}),
    "AQDCuidadorResult": frozenset({"puntaje_total"}),
    "AQDParticipanteResult": frozenset({"puntaje_total"}),
    "RedLatSpanishResult": frozenset({"puntaje_total"}),
    "PuntajeCDRResult": frozenset({"suma_cajas"}),  # resumen aparte, no fila suelta
    "MEWResult": frozenset({"puntuacion"}),  # va en banner «Puntuación total MEQ»
    # D-16/D-18/D-20: derivados van en banner
    "PittsburghResult": frozenset({"puntuacion_total"}),
    "EpworthResult": frozenset({"puntaje_total"}),
    "AtenasResult": frozenset({"puntuacion_total"}),
    "ISIResult": frozenset({"puntuacion_total"}),
    "StopBangResult": frozenset({"puntaje_total"}),
    "BerlinResult": frozenset({
        "categoria1_positiva", "categoria2_positiva", "categoria3_positiva",
        "categorias_positivas", "riesgo",
    }),
    "BettyFerrelResult": frozenset({"puntaje_total", "promedio_global"}),
    "EuroQol5D5LResult": frozenset({"estado_salud"}),
    "CuidadorNPIResult": frozenset({"puntaje_total"}),
    "MoCAResult": frozenset({"puntaje_total"}),
}


def _resolver_scores_vista(resultado):
    """Decide qué resumen de puntaje mostrar en ver/impresión.

    - Yesavage / AQD / RedLat: sin caja de total (RedLat ya lista componentes).
    - CDR: resalta CDR Global; calcula en vivo la suma de los 6 dominios.
    - MEW: ``puntuacion`` → banner «Puntuación total MEQ».
    - Sueño / Betty / MoCA / EuroQoL / NPI: total + interpretación en detalle.
    """
    from apps.home.services.exam_scoring import (
        interpretar_epworth,
        interpretar_psqi,
        interpretar_atenas,
        interpretar_isi,
        interpretar_stopbang,
        interpretar_betty,
        interpretar_yesavage,
    )

    model_name = type(resultado).__name__
    out = {
        "puntaje_total": None,
        "suma_cajas": None,
        "cdr_global": None,
        "score_banner_titulo": None,
        "score_banner_valor": None,
        "score_banner_detalle": None,
        "aqd_anosognosia": None,
    }

    if model_name == "PuntajeCDRResult":
        cdr_global = getattr(resultado, "cdr_global", None)
        suma = None
        if hasattr(resultado, "calcular_suma_cajas"):
            suma = resultado.calcular_suma_cajas()
        else:
            suma = getattr(resultado, "suma_cajas", None)
        out["cdr_global"] = cdr_global
        out["suma_cajas"] = suma
        out["score_banner_titulo"] = "CDR Global"
        out["score_banner_valor"] = cdr_global
        if suma is not None:
            out["score_banner_detalle"] = (
                f"Suma de los 6 dominios (cajas): {suma:g}"
            )
        return out

    if model_name == "MEWResult":
        puntuacion = getattr(resultado, "puntuacion", None)
        out["puntaje_total"] = puntuacion
        out["score_banner_titulo"] = "Puntuación total MEQ"
        out["score_banner_valor"] = puntuacion
        tipo = getattr(resultado, "tipo_persona", None)
        if tipo:
            out["score_banner_detalle"] = str(tipo)
        return out

    if model_name == "PittsburghResult":
        total = getattr(resultado, "puntuacion_total", None)
        out["puntaje_total"] = total
        out["score_banner_titulo"] = "Puntaje Total PSQI"
        out["score_banner_valor"] = total
        interp = getattr(resultado, "interpretacion", None) or (
            interpretar_psqi(total) if total is not None else None
        )
        comps = [
            getattr(resultado, f"componente_{c}", None)
            for c in (
                "calidad", "latencia", "duracion", "eficiencia",
                "perturbaciones", "medicacion", "disfuncion",
            )
        ]
        detalle_parts = []
        if any(c is not None for c in comps):
            detalle_parts.append(
                "Componentes: "
                + " · ".join(
                    f"{n}={v if v is not None else '—'}"
                    for n, v in zip(
                        ("C1", "C2", "C3", "C4", "C5", "C6", "C7"), comps
                    )
                )
            )
        if interp:
            detalle_parts.append(str(interp))
        out["score_banner_detalle"] = " | ".join(detalle_parts) or None
        return out

    if model_name == "EpworthResult":
        total = getattr(resultado, "puntaje_total", None)
        out["puntaje_total"] = total
        out["score_banner_titulo"] = "Puntaje Total"
        out["score_banner_valor"] = total
        interp = getattr(resultado, "interpretacion", None) or (
            interpretar_epworth(total) if total is not None else None
        )
        out["score_banner_detalle"] = interp
        return out

    if model_name == "AtenasResult":
        total = getattr(resultado, "puntuacion_total", None)
        out["puntaje_total"] = total
        out["score_banner_titulo"] = "Puntaje Total"
        out["score_banner_valor"] = total
        out["score_banner_detalle"] = getattr(
            resultado, "interpretacion", None
        ) or (interpretar_atenas(total) if total is not None else None)
        return out

    if model_name == "ISIResult":
        total = getattr(resultado, "puntuacion_total", None)
        out["puntaje_total"] = total
        out["score_banner_titulo"] = "Puntaje Total"
        out["score_banner_valor"] = total
        out["score_banner_detalle"] = getattr(
            resultado, "interpretacion", None
        ) or (interpretar_isi(total) if total is not None else None)
        return out

    if model_name == "StopBangResult":
        total = getattr(resultado, "puntaje_total", None)
        out["puntaje_total"] = total
        out["score_banner_titulo"] = "Puntaje Total STOP-Bang"
        out["score_banner_valor"] = total
        riesgo = getattr(resultado, "riesgo", None)
        stop = getattr(resultado, "stop_positivos", None)
        bang = getattr(resultado, "bang_positivos", None)
        scored = interpretar_stopbang(
            total, stop, bang, getattr(resultado, "alto_riesgo_alternativo", None)
        )
        parts = []
        if stop is not None or bang is not None:
            parts.append(f"STOP={stop or 0} · BANG={bang or 0}")
        parts.append(f"Riesgo: {riesgo or scored['riesgo']}")
        parts.append(scored["interpretacion"])
        out["score_banner_detalle"] = " | ".join(parts)
        return out

    if model_name == "BerlinResult":
        riesgo = getattr(resultado, "riesgo", None)
        positivas = getattr(resultado, "categorias_positivas", None)
        out["score_banner_titulo"] = "Riesgo Berlín"
        out["score_banner_valor"] = riesgo or "—"
        c1 = getattr(resultado, "categoria1_positiva", None)
        c2 = getattr(resultado, "categoria2_positiva", None)
        c3 = getattr(resultado, "categoria3_positiva", None)
        interp = getattr(resultado, "interpretacion", None)
        parts = [
            f"Categorías positivas: {positivas if positivas is not None else '—'}",
            f"C1={'Sí' if c1 else 'No' if c1 is not None else '—'} · "
            f"C2={'Sí' if c2 else 'No' if c2 is not None else '—'} · "
            f"C3={'Sí' if c3 else 'No' if c3 is not None else '—'}",
        ]
        if interp:
            parts.append(str(interp))
        out["score_banner_detalle"] = " | ".join(parts)
        return out

    if model_name == "BettyFerrelResult":
        global_avg = getattr(resultado, "promedio_global", None)
        out["puntaje_total"] = getattr(resultado, "puntaje_total", None)
        out["score_banner_titulo"] = "Promedio global QOL"
        out["score_banner_valor"] = global_avg
        interp = getattr(resultado, "interpretacion", None) or interpretar_betty(
            global_avg
        )
        dims = []
        for label, attr in (
            ("Físico", "promedio_fisico"),
            ("Psicológico", "promedio_psicologico"),
            ("Social", "promedio_social"),
            ("Espiritual", "promedio_espiritual"),
        ):
            v = getattr(resultado, attr, None)
            if v is not None:
                dims.append(f"{label}={v}")
        detalle = " · ".join(dims)
        if interp:
            detalle = f"{detalle} | {interp}" if detalle else interp
        out["score_banner_detalle"] = detalle or None
        return out

    if model_name == "EuroQol5D5LResult":
        codigo = getattr(resultado, "estado_salud", None)
        out["score_banner_titulo"] = "Estado de salud EQ-5D"
        out["score_banner_valor"] = codigo or "—"
        out["score_banner_detalle"] = (
            "Código de 5 dígitos (sin índice de utilidad)"
        )
        return out

    if model_name == "EuroQolEVASaludResult":
        vas = getattr(resultado, "termometro_estado_salud", None)
        out["puntaje_total"] = vas
        out["score_banner_titulo"] = "EQ-VAS"
        out["score_banner_valor"] = vas
        out["score_banner_detalle"] = "Autovaloración 0–100"
        return out

    if model_name == "CuidadorNPIResult":
        total = getattr(resultado, "puntaje_total", None)
        carga = getattr(resultado, "carga_total", None)
        out["puntaje_total"] = total
        out["score_banner_titulo"] = "Puntaje total NPI"
        out["score_banner_valor"] = total
        if carga is not None:
            out["score_banner_detalle"] = f"Carga total (distrés): {carga}"
        return out

    if model_name == "MoCAResult":
        total = getattr(resultado, "puntaje_total", None)
        out["puntaje_total"] = total
        out["score_banner_titulo"] = "Puntaje Total MoCA"
        out["score_banner_valor"] = total
        parts = []
        interp = getattr(resultado, "interpretacion", None)
        if interp:
            parts.append(str(interp))
        mis = getattr(resultado, "mis", None)
        if mis is not None:
            parts.append(f"MIS: {mis}")
        out["score_banner_detalle"] = " | ".join(parts) or None
        return out

    if model_name == "ParticipanteYesavageResult":
        # Sin caja de total (política B-10); sí mostrar interpretación si hay
        interp = getattr(resultado, "interpretacion", None)
        if not interp or str(interp).strip() in ("0", ""):
            pt = getattr(resultado, "puntaje_total", None)
            if pt is not None:
                interp = interpretar_yesavage(pt)
        if interp and str(interp).strip() not in ("0", ""):
            out["score_banner_titulo"] = "Interpretación Yesavage"
            out["score_banner_valor"] = interp
        return out

    if model_name in _OCULTAR_PUNTAJE_TOTAL:
        return out

    puntaje_total = getattr(resultado, "puntaje_total", None)
    if puntaje_total is None:
        puntaje_total = getattr(resultado, "puntuacion_total", None)
    if puntaje_total is None:
        puntaje_total = getattr(resultado, "puntuacion", None)
    out["puntaje_total"] = puntaje_total
    if puntaje_total is not None:
        out["score_banner_titulo"] = "Puntaje Total"
        out["score_banner_valor"] = puntaje_total
        interp = getattr(resultado, "interpretacion", None)
        if interp and str(interp).strip() not in ("0", ""):
            out["score_banner_detalle"] = str(interp)
    return out


def _resolver_aqd_anosognosia(visita_examen, resultado):
    """Si la visita tiene ambos AQD, calcula delta de anosognosia (D-17)."""
    model_name = type(resultado).__name__
    if model_name not in ("AQDCuidadorResult", "AQDParticipanteResult"):
        return None
    try:
        from apps.home.models import AQDCuidadorResult, AQDParticipanteResult
        from apps.home.services.exam_scoring import interpretar_aqd_anosognosia
    except Exception:
        return None

    visita = visita_examen.visita
    cuid = (
        AQDCuidadorResult.objects.filter(visita_examen__visita=visita)
        .order_by("-id")
        .first()
    )
    part = (
        AQDParticipanteResult.objects.filter(visita_examen__visita=visita)
        .order_by("-id")
        .first()
    )
    if not cuid or not part:
        return None
    return interpretar_aqd_anosognosia(cuid.puntaje_total, part.puntaje_total)

def _campos_ocultos_resultado(resultado):
    model_name = type(resultado).__name__
    extra = _CAMPOS_OCULTOS_POR_MODELO.get(model_name, frozenset())
    return _CAMPOS_OMITIR_SECCIONES | extra


def _es_flag_seccion_evaluado(field_name: str) -> bool:
    return field_name.startswith("seccion_") and field_name.endswith("_evaluado")


# Título de PRINT_SECCIONES_INICIOS → nombre del flag B-09
_SECCION_EVALUADO_POR_TITULO = {
    # Neurológico
    "I Par Craneal — Olfatorio": "seccion_pares_craneales_evaluado",
    "II Par Craneal — Óptico": "seccion_pares_craneales_evaluado",
    "III, IV y VI Par Craneal — Oculomotores": "seccion_pares_craneales_evaluado",
    "V Par Craneal — Trigémino": "seccion_pares_craneales_evaluado",
    "VII Par Craneal — Facial": "seccion_pares_craneales_evaluado",
    "VIII Par Craneal — Auditivo": "seccion_pares_craneales_evaluado",
    "IX y X Par Craneal — Glosofaríngeo y Vago": "seccion_pares_craneales_evaluado",
    "XI Par Craneal — Espinal accesorio": "seccion_pares_craneales_evaluado",
    "XII Par Craneal — Hipogloso": "seccion_pares_craneales_evaluado",
    "Sensibilidad": "seccion_sensibilidad_evaluado",
    "Reflejos": "seccion_reflejos_evaluado",
    "Fuerza muscular": "seccion_fuerza_evaluado",
    "Coordinación": "seccion_coordinacion_marcha_evaluado",
    "Marcha": "seccion_coordinacion_marcha_evaluado",
    "Movimientos anormales": "seccion_coordinacion_marcha_evaluado",
    # Físico
    "Signos vitales": "seccion_signos_vitales_evaluado",
    "Cabeza y cuello": "seccion_cabeza_cuello_evaluado",
    "Tórax / Cardio / Respiratorio": "seccion_torax_evaluado",
    "Abdomen": "seccion_abdomen_evaluado",
    "Osteomuscular": "seccion_osteomuscular_evaluado",
    "Piel y anexos": "seccion_piel_evaluado",
}


def _construir_secciones(resultado):
    """Agrupa los campos del resultado en subsecciones (A-06 / B-09).

    Usa ``type(resultado).PRINT_SECCIONES_INICIOS`` (lista ordenada de
    ``(campo_inicial, título)``). Devuelve ``None`` si el modelo no lo define.
    Si una sección gruesa está marcada No evaluado (B-09), emite solo
    ``("Estado", "No evaluado")`` y omite el detalle de toggles.
    """
    inicios = getattr(type(resultado), "PRINT_SECCIONES_INICIOS", None)
    if not inicios:
        return None

    inicio_map = dict(inicios)
    secciones = []
    actual = {"titulo": "General", "campos": []}
    actual_no_evaluado = False

    def _flush():
        nonlocal actual, actual_no_evaluado
        if actual_no_evaluado:
            secciones.append(
                {"titulo": actual["titulo"], "campos": [("Estado", "No evaluado")]}
            )
        elif actual["campos"]:
            secciones.append(actual)
        actual_no_evaluado = False

    for field in resultado._meta.fields:
        if field.name in _CAMPOS_OMITIR_SECCIONES:
            continue
        if field.name in _CAMPOS_OCULTOS_POR_MODELO.get(type(resultado).__name__, ()):
            continue
        if _es_flag_seccion_evaluado(field.name):
            continue
        if field.name in inicio_map:
            _flush()
            titulo = inicio_map[field.name]
            actual = {"titulo": titulo, "campos": []}
            flag = _SECCION_EVALUADO_POR_TITULO.get(titulo)
            if flag and hasattr(resultado, flag) and not getattr(resultado, flag):
                actual_no_evaluado = True
        if actual_no_evaluado:
            continue
        valor = _formatear_valor_campo(resultado, field)
        if valor in (None, ""):
            continue
        etiqueta = str(field.verbose_name) if field.verbose_name else field.name
        actual["campos"].append((etiqueta, valor))

    _flush()

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
    ocultos = _campos_ocultos_resultado(resultado)
    for field in resultado._meta.fields:
        if field.name in ocultos or _es_flag_seccion_evaluado(field.name):
            continue
        etiqueta = str(field.verbose_name) if field.verbose_name else field.name
        datos_resultado[etiqueta] = _formatear_valor_campo(resultado, field)

    proyecto = visita_examen.visita.Tipo_visita.proyecto
    codigo_proyecto = (
        ProyectoPacienteExtra.objects.filter(proyecto=proyecto, paciente=paciente)
        .values_list("codigo_proyecto", flat=True)
        .first()
    )
    scores = _resolver_scores_vista(resultado)
    aqd_anosognosia = _resolver_aqd_anosognosia(visita_examen, resultado)
    if aqd_anosognosia:
        scores["aqd_anosognosia"] = aqd_anosognosia

    return (
        "examenes_resultados/resultado_generico.html",
        {
            "visita_examen": visita_examen,
            "resultado": resultado,
            "datos_resultado": datos_resultado,
            "secciones": _construir_secciones(resultado),
            "paciente": paciente,
            "codigo_proyecto": codigo_proyecto,
            **scores,
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
