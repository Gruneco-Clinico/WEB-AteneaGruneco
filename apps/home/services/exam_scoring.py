# -*- encoding: utf-8 -*-
"""
Cálculo puro de puntajes e interpretaciones clínicas (Épica D).

Usado por ModelForms (persistencia) y por ``exam_view_context`` (ver/PDF)
para que la vista no dependa solo de etiquetas JS de edición.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def _int(val: Any, default: int = 0) -> int:
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _norm(val: Any) -> str:
    return str(val or "").strip().lower()


# ─── Epworth ─────────────────────────────────────────────────────────────────

def interpretar_epworth(puntaje: Any) -> str:
    """0–5 normal · 6–10 media · 11–15 moderada · 16–24 severa."""
    p = _int(puntaje)
    if p <= 5:
        return "Somnolencia diurna normal"
    if p <= 10:
        return "Somnolencia diurna media"
    if p <= 15:
        return "Somnolencia diurna moderada"
    return "Somnolencia diurna severa"


# ─── PSQI ────────────────────────────────────────────────────────────────────

def interpretar_psqi(puntuacion_total: Any) -> str:
    total = _int(puntuacion_total)
    if total <= 5:
        return "Duerme bien (buena calidad de sueño)"
    return "Duerme mal (mala calidad de sueño)"


# ─── Atenas / ISI / MEW ──────────────────────────────────────────────────────

def interpretar_atenas(puntuacion_total: Any) -> str:
    p = _int(puntuacion_total)
    if p <= 5:
        return "Sin problemas de sueño"
    if p <= 10:
        return "Problemas leves de sueño"
    if p <= 15:
        return "Problemas moderados de sueño"
    return "Problemas severos de sueño"


def interpretar_isi(puntuacion_total: Any) -> str:
    p = _int(puntuacion_total)
    if p <= 7:
        return "Sin insomnio clínicamente significativo"
    if p <= 14:
        return "Insomnio subclínico (leve)"
    if p <= 21:
        return "Insomnio clínico (moderado)"
    return "Insomnio clínico (severo)"


def cronotipo_mew(puntuacion: Any) -> str:
    p = _int(puntuacion)
    if p >= 70:
        return "Definitivamente matutino"
    if p >= 59:
        return "Moderadamente matutino"
    if p >= 42:
        return "Ni matutino ni vespertino"
    if p >= 31:
        return "Moderadamente vespertino"
    return "Definitivamente vespertino"


# ─── Stop-Bang ───────────────────────────────────────────────────────────────

def interpretar_stopbang(
    puntaje_total: Any,
    stop_positivos: Any = None,
    bang_positivos: Any = None,
    alto_riesgo_alternativo: Any = None,
) -> Dict[str, Any]:
    total = _int(puntaje_total)
    stop = _int(stop_positivos)
    bang = _int(bang_positivos)
    alt = bool(alto_riesgo_alternativo) if alto_riesgo_alternativo is not None else (
        stop >= 2 and bang >= 2
    )

    if total >= 5 or alt:
        riesgo = "Alto"
        texto = (
            "Alto riesgo de apnea obstructiva del sueño. "
            "Se recomienda evaluación especializada."
        )
    elif total >= 3:
        riesgo = "Intermedio"
        texto = (
            "Riesgo intermedio de apnea obstructiva del sueño. "
            "Considere evaluación adicional."
        )
    else:
        riesgo = "Bajo"
        texto = "Bajo riesgo de apnea obstructiva del sueño."

    return {
        "riesgo": riesgo,
        "interpretacion": texto,
        "alto_riesgo_alternativo": alt,
    }


# ─── Berlín ──────────────────────────────────────────────────────────────────

_FREQ_ALTA = ("casi todos los días", "3-4 veces", "3–4 veces", "3 a 4")


def _freq_alta(val: Any) -> bool:
    s = _norm(val)
    return any(x in s for x in _FREQ_ALTA)


def _volumen_alto(val: Any) -> bool:
    s = _norm(val)
    return (
        "más fuerte" in s
        or "muy alto" in s
        or "otras habitaciones" in s
        or "mas fuerte" in s
    )


def score_berlin(data: Mapping[str, Any]) -> Dict[str, Any]:
    """Categorías positivas + riesgo según Word de interpretación Berlín."""
    cat1_riesgos = 0
    if _volumen_alto(data.get("tipo_ronquido")):
        cat1_riesgos += 1
    if _freq_alta(data.get("frecuencia_ronquidos")):
        cat1_riesgos += 1
    if _norm(data.get("ronquido_molesto")) in ("si", "sí", "true", "1"):
        cat1_riesgos += 1
    if _freq_alta(data.get("apnea_observada")):
        cat1_riesgos += 1
    # Ronca sí cuenta como contexto; la categoría usa respuestas de riesgo ≥2
    cat1_positiva = cat1_riesgos >= 2

    cat2_riesgos = 0
    if _freq_alta(data.get("fatiga_matutina")):
        cat2_riesgos += 1
    if _freq_alta(data.get("fatiga_dia")):
        cat2_riesgos += 1
    somnolencia = data.get("somnolencia_conducir")
    if somnolencia in (True, "True", "true", "1", "si", "sí", "Sí"):
        cat2_riesgos += 1
    cat2_positiva = cat2_riesgos >= 2

    presion = data.get("presion_alta")
    hta = presion in (True, "True", "true", "1", "si", "sí", "Sí")
    imc = _float(data.get("imc"), default=-1.0)
    obesidad = imc > 30 if imc >= 0 else False
    cat3_positiva = hta or obesidad

    positivas = sum([cat1_positiva, cat2_positiva, cat3_positiva])
    if positivas >= 2:
        riesgo = "Alto"
        interpretacion = "Alto riesgo de apnea del sueño (SAOS)"
    else:
        riesgo = "Bajo"
        interpretacion = "Bajo riesgo de apnea del sueño (SAOS)"

    return {
        "categoria1_positiva": cat1_positiva,
        "categoria2_positiva": cat2_positiva,
        "categoria3_positiva": cat3_positiva,
        "categorias_positivas": positivas,
        "riesgo": riesgo,
        "interpretacion": interpretacion,
    }


# ─── AQD anosognosia ─────────────────────────────────────────────────────────

def interpretar_aqd_anosognosia(
    total_cuidador: Any, total_participante: Any
) -> Dict[str, Any]:
    """delta = cuidador − participante; ≥10 Con Anosognosia."""
    c = _int(total_cuidador)
    p = _int(total_participante)
    delta = c - p
    if delta >= 10:
        texto = "Sin conciencia (Con Anosognosia)"
    else:
        texto = "Con conciencia (Sin Anosognosia)"
    return {
        "delta": delta,
        "total_cuidador": c,
        "total_participante": p,
        "interpretacion": texto,
    }


# ─── Yesavage (GDS-15) ───────────────────────────────────────────────────────
# Orden alineado al template: SI en 2,3,4,6,8,9,10,12,14,15; NO en 1,5,7,11,13.

_YESAVAGE_PUNTA_SI = frozenset({
    "disminuir_actividades",
    "vida_vacia",
    "aburrido_frecuente",
    "preocupacion",
    "frecuencia_desamparado",
    "quedarse_casa",
    "problemas_memoria",
    "inutil",
    "sin_esperanza",
    "otras_personas_mejor",
})
_YESAVAGE_PUNTA_NO = frozenset({
    "satisfaccion_vida",
    "buen_animo",
    "felicidad",
    "maravilla_vivir",
    "lleno_energia",
})


def score_yesavage(data: Mapping[str, Any]) -> Dict[str, Any]:
    """GDS-15: recalcula total e interpretación en servidor."""
    total = 0
    for field, val in data.items():
        v = _norm(val)
        if field in _YESAVAGE_PUNTA_SI and v == "si":
            total += 1
        elif field in _YESAVAGE_PUNTA_NO and v == "no":
            total += 1
    interpretacion = interpretar_yesavage(total)
    return {"puntaje_total": total, "interpretacion": interpretacion}


def interpretar_yesavage(puntaje: Any) -> str:
    p = _int(puntaje)
    if p <= 5:
        return "Normal"
    if p <= 9:
        return "Depresión leve"
    return "Depresión establecida"


# ─── MoCA ────────────────────────────────────────────────────────────────────

def score_concentracion_moca(errores: Any) -> Tuple[int, str]:
    """Ítem 6: 0–1 error → 1 punto; >1 → 0."""
    e = _int(errores)
    if e <= 1:
        return 1, "no_fallo"
    return 0, "fallo"


def interpretar_moca(puntaje: Any) -> str:
    pt = _int(puntaje)
    if pt >= 26:
        return "Normal"
    if pt >= 18:
        return "Deterioro cognitivo leve"
    return "Deterioro cognitivo significativo"


def score_mis_moca(
    free: Sequence[bool],
    category: Sequence[bool],
    multiple: Sequence[bool],
) -> int:
    """MIS = free×3 + category×2 + multiple×1 por palabra (máx. 15)."""
    total = 0
    n = max(len(free), len(category), len(multiple), 5)
    for i in range(n):
        f = bool(free[i]) if i < len(free) else False
        c = bool(category[i]) if i < len(category) else False
        m = bool(multiple[i]) if i < len(multiple) else False
        if f:
            total += 3
        elif c:
            total += 2
        elif m:
            total += 1
    return min(total, 15)


# ─── Betty Ferrell ───────────────────────────────────────────────────────────

BETTY_FISICO = (
    "agotamiento",
    "cambios_alimenticios",
    "dolor",
    "cambios_sueno",
    "salud_fisica_general",
)
BETTY_PSICOLOGICO = (
    "facilidad_enfrentar",
    "felicidad",
    "control_vida",
    "satisfaccion_vida",
    "concentracion",
    "utilidad_personal",
    "angustia_diagnostico",
    "angustia_tratamiento",
    "ansiedad",
    "depresion",
    "miedo_otra_enfermedad",
    "miedo_retroceso",
    "miedo_avance",
    "estado_psicologico",
)
BETTY_SOCIAL = (
    "angustia_familiar",
    "nivel_ayuda",
    "relaciones_personales",
    "vida_sexual",
    "trabajo",
    "actividades_hogar",
    "aislamiento",
    "carga_economica",
    "estado_social",
)
BETTY_ESPIRITUAL = (
    "actividades_religiosas",
    "actividades_espirituales_personales",
    "incertidumbre_futuro",
    "cambios_positivos",
    "proposito_vida",
    "esperanza",
    "estado_espiritual",
)

# Ítems de bienestar (positivos): invertir 5 − valor para que alto = más problema.
BETTY_ITEMS_INVERTIR = frozenset({
    "salud_fisica_general",
    "facilidad_enfrentar",
    "felicidad",
    "control_vida",
    "satisfaccion_vida",
    "concentracion",
    "utilidad_personal",
    "estado_psicologico",
    "nivel_ayuda",
    "relaciones_personales",
    "vida_sexual",
    "trabajo",
    "actividades_hogar",
    "estado_social",
    "actividades_religiosas",
    "actividades_espirituales_personales",
    "cambios_positivos",
    "proposito_vida",
    "esperanza",
    "estado_espiritual",
})


def _betty_valor(raw: Any, invertir: bool) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        # Puede venir "3" o "3 - texto"
        s = str(raw).strip().split()[0]
        v = float(s)
    except (TypeError, ValueError):
        return None
    if v < 1 or v > 4:
        return None
    return (5.0 - v) if invertir else v


def _betty_promedio(data: Mapping[str, Any], fields: Sequence[str]) -> Optional[float]:
    vals: List[float] = []
    for f in fields:
        v = _betty_valor(data.get(f), f in BETTY_ITEMS_INVERTIR)
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


def score_betty(data: Mapping[str, Any]) -> Dict[str, Any]:
    fisico = _betty_promedio(data, BETTY_FISICO)
    psico = _betty_promedio(data, BETTY_PSICOLOGICO)
    social = _betty_promedio(data, BETTY_SOCIAL)
    espiritual = _betty_promedio(data, BETTY_ESPIRITUAL)
    dims = [d for d in (fisico, psico, social, espiritual) if d is not None]
    global_avg = round(sum(dims) / len(dims), 2) if dims else None

    # Puntaje bruto (suma invertida) para compatibilidad con campo IntegerField
    bruto = 0
    for fields in (BETTY_FISICO, BETTY_PSICOLOGICO, BETTY_SOCIAL, BETTY_ESPIRITUAL):
        for f in fields:
            v = _betty_valor(data.get(f), f in BETTY_ITEMS_INVERTIR)
            if v is not None:
                bruto += int(round(v))

    interpretacion = interpretar_betty(global_avg)
    return {
        "promedio_fisico": fisico,
        "promedio_psicologico": psico,
        "promedio_social": social,
        "promedio_espiritual": espiritual,
        "promedio_global": global_avg,
        "puntaje_total": bruto,
        "interpretacion": interpretacion,
    }


def interpretar_betty(promedio_global: Any) -> str:
    if promedio_global is None or promedio_global == "":
        return ""
    g = _float(promedio_global)
    if g <= 2.0:
        return "Calidad de vida alta (afectación baja/ausente)"
    if g <= 3.0:
        return "Calidad de vida media (afectación moderada)"
    return "Calidad de vida baja (afectación alta/severa)"


# ─── EuroQoL ─────────────────────────────────────────────────────────────────

_EQ5D_LEVEL_KEYWORDS = (
    # orden: nivel 1 … 5 (sin problemas → extremo)
    (("no tengo", "no estoy", "ningún"), 1),
    (("leve", "levemente"), 2),
    (("moderado", "moderadamente"), 3),
    (("severo", "severamente", "grave"), 4),
    (("extremo", "extremadamente", "incapaz", "en la cama"), 5),
)


def nivel_eq5d(texto: Any) -> Optional[int]:
    """Mapea texto de opción o dígito 1–5 a nivel EQ-5D-5L."""
    if texto is None or texto == "":
        return None
    s = str(texto).strip()
    if s.isdigit():
        n = int(s)
        return n if 1 <= n <= 5 else None
    low = s.lower()
    # Priorizar extremos / severidad antes que "no"
    for keywords, level in reversed(_EQ5D_LEVEL_KEYWORDS):
        if any(k in low for k in keywords):
            # Evitar que "no tengo" coincida con nivel 5 por "incapaz"
            if level == 5 and any(k in low for k in ("no tengo", "no estoy")):
                continue
            return level
    # Fallback ordenado de menos a más severo
    for keywords, level in _EQ5D_LEVEL_KEYWORDS:
        if any(k in low for k in keywords):
            return level
    return None


def codigo_estado_eq5d(
    movilidad: Any,
    cuidado_personal: Any,
    actividades: Any,
    dolor: Any,
    ansiedad: Any,
) -> Optional[str]:
    niveles = [
        nivel_eq5d(movilidad),
        nivel_eq5d(cuidado_personal),
        nivel_eq5d(actividades),
        nivel_eq5d(dolor),
        nivel_eq5d(ansiedad),
    ]
    if any(n is None for n in niveles):
        return None
    return "".join(str(n) for n in niveles)
