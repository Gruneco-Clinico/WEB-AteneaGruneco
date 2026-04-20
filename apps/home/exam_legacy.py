# -*- coding: utf-8 -*-
"""
IDs de exámenes que usan el flujo legacy en realizar_examen (plantilla fija + modelo *Result).
Cualquier otro examen_id definido en BD con Examen.campos no vacío usa el Form Builder.
"""
LEGACY_REALIZAR_EXAMEN_IDS = frozenset(
    {
        3,
        4,
        5,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
        40,
    }
)


def is_legacy_examen(examen_id) -> bool:
    try:
        return int(examen_id) in LEGACY_REALIZAR_EXAMEN_IDS
    except (TypeError, ValueError):
        return False


def examen_has_builder_schema(campos) -> bool:
    """True si ``Examen.campos`` define al menos un nodo del form builder."""
    from .form_builder.schema import normalize_schema

    return bool(normalize_schema(campos))
