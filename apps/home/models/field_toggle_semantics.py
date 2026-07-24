# -*- encoding: utf-8 -*-
"""
Semántica de toggles booleanos (B-08) para examen físico/neurológico.

Tipos:
  - detecta: True=Detecta, False=No detecta (default True)
  - sintoma: True=Presente, False=Ausente (default False = normal)
  - estructura: True=Normal, False=Anormal (default True)

El mapeo es refinable con Carlos; no reescribe datos históricos.
"""
from __future__ import annotations

TOGGLE_LABELS = {
    "detecta": {True: "Detecta", False: "No detecta"},
    "sintoma": {True: "Presente", False: "Ausente"},
    "estructura": {True: "Normal", False: "Anormal"},
}

TOGGLE_DEFAULTS = {
    "detecta": True,
    "sintoma": False,
    "estructura": True,
}

# Prefijos olfatorios (par I) → detecta
_NEURO_DETECTA_PREFIXES = (
    "clavos_",
    "pimienta_",
    "cafe_",
    "canela_",
    "alcohol_",
)

# Síntomas / hallazgos (True = presente = alteración)
_NEURO_SINTOMAS = frozenset(
    {
        "amaurosis",
        "oscurecimientos",
        "fotopsias",
        "escotomas",
        "agudeza_visual",
        "hemorragias",
        "exudados",
        "diplopia",
        "ptosis_palpebral",
        "desviaciones_oculares",
        "hipoacusia",
        "tinitus",
        "acufenos",
        "vertigo",
        "mareo",
        "nistagmus",
        "disfonia",
        "afonia",
        "voz_nasal",
        "disfagia",
        "sialorrea",
        "dolor_faringe",
        "atrofia_lingual",
        "fasciculaciones_linguales",
        "marcha_hemiplejica",
        "marcha_parkinsoniana",
        "marcha_espastica",
        "marcha_polineuritica",
        "marcha_ataxica",
        "marcha_miopatica",
        "marcha_steppage",
        "convulsiones",
        "fasciculaciones",
        "mioclonias",
        "temblores",
        "corea",
        "espasmos",
        "balismos",
        "calambres",
        "tics",
        "distonias",
    }
)

# Examen físico: hallazgos cutáneos / abdominales (Presente/Ausente)
_FISICO_SINTOMAS = frozenset(
    {
        "ruidos_sobreagregados",
        "masas",
        "megalias",
        "maculas",
        "papulas",
        "vesiculas",
        "pustulas",
        "fisuras",
        "escaras",
        "petequias",
        "equimosis",
        "ulceras",
    }
)

# Pares normal/anormal del físico: solo el campo *_normal usa semántica estructura
_FISICO_ESTRUCTURA_SUFFIX = "_normal"


def neuro_toggle_tipo(field_name: str) -> str | None:
    if any(field_name.startswith(p) for p in _NEURO_DETECTA_PREFIXES):
        return "detecta"
    if field_name in _NEURO_SINTOMAS:
        return "sintoma"
    # Flags B-09 no son toggles de hallazgo
    if field_name.endswith("_evaluado") or field_name.startswith("seccion_"):
        return None
    return "estructura"


def fisico_toggle_tipo(field_name: str) -> str | None:
    if field_name in _FISICO_SINTOMAS:
        return "sintoma"
    if field_name.endswith(_FISICO_ESTRUCTURA_SUFFIX):
        return "estructura"
    # *_anormal se omite de semántica (el par *_normal ya cubre Normal/Anormal)
    if field_name.endswith("_anormal"):
        return None
    if field_name.endswith("_evaluado") or field_name.startswith("seccion_"):
        return None
    return None


def build_field_toggle_semantics(model_cls) -> dict[str, str]:
    """Construye {campo: tipo} para los booleanos del modelo."""
    from django.db.models import BooleanField

    getter = (
        neuro_toggle_tipo
        if model_cls.__name__ == "ExamenNeurologicoResult"
        else fisico_toggle_tipo
    )
    out = {}
    for field in model_cls._meta.fields:
        if not isinstance(field, BooleanField):
            continue
        tipo = getter(field.name)
        if tipo:
            out[field.name] = tipo
    return out


def formatear_toggle(tipo: str, valor: bool) -> str:
    labels = TOGGLE_LABELS.get(tipo)
    if not labels:
        return "Sí" if valor else "No"
    return labels[bool(valor)]


def default_datos_toggles(model_cls) -> dict:
    """Valores por defecto para precarga de formulario nuevo."""
    semantics = getattr(model_cls, "FIELD_TOGGLE_SEMANTICS", None)
    if semantics is None:
        semantics = build_field_toggle_semantics(model_cls)
    return {
        name: TOGGLE_DEFAULTS[tipo]
        for name, tipo in semantics.items()
        if tipo in TOGGLE_DEFAULTS
    }
