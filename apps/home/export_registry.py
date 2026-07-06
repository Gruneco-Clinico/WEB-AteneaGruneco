# -*- encoding: utf-8 -*-
"""
Registro de campos exportables por examen (CSV proyectos).

Complementa exam_registry.py con alias y extracción de tablas hijas / Form Builder.
"""
import json

from .exam_registry import get_exam_config, get_exam_model

# Campos exportables por examen_id → lista de nombres de atributo en el modelo resultado
EXPORT_FIELD_REGISTRY = {
    13: {  # Pittsburgh
        "fields": [
            "puntuacion_total",
            "interpretacion",
            "hora_acostarse",
            "hora_levantarse",
            "latencia_sueno",
        ],
        "aliases": {"puntuacion_total": "puntaje_total"},
    },
    14: {  # Epworth
        "fields": ["puntaje_total", "interpretacion"],
        "aliases": {},
    },
    16: {  # MEW
        "fields": ["puntuacion", "tipo_persona"],
        "aliases": {"puntuacion": "puntaje_total"},
    },
    19: {  # ISI
        "fields": ["puntuacion_total", "interpretacion"],
        "aliases": {},
    },
    10: {  # Anamnesis sueño
        "fields": ["motivo_consulta", "enfermedad_actual", "presenta_queja"],
        "child_tables": {
            "sustancias": ["nombre", "frecuencia"],
            "medicamentos": ["nombre", "dosis"],
        },
    },
    5: {  # Antecedentes
        "child_tables": {
            "antecedentes_patologicos": ["tipo_patologia", "tiempo_evolucion"],
            "antecedentes_farmacologicos": ["medicamento", "dosis"],
        },
    },
    7: {  # Análisis general
        "fields": ["motivo_consulta", "enfermedad_actual", "plan_manejo"],
        "child_tables": {
            "diagnosticos_cie10": ["codigo", "descripcion"],
        },
    },
}

# Etiquetas legibles para columnas CSV genéricas
CAMPO_EXAMEN_LABELS = {
    "motivo_consulta": "Motivo Consulta",
    "puntaje_total": "Puntaje",
    "puntuacion_total": "Puntaje",
    "puntuacion": "Puntaje",
    "interpretacion": "Interpretación",
    "observaciones": "Observaciones",
    "estado_examen": "Estado Examen",
    "evaluador": "Evaluador",
    "notas_visita": "Notas Visita",
    "resultados_tabla": "Resultados (JSON)",
}

_TABLA_SKIP_FIELDS = frozenset({"id", "pk", "visita_examen"})
_META_SKIP_SUFFIXES = ("_ptr",)


def _serialize_export_value(val):
    from datetime import date, datetime, time

    if val is None:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%d/%m/%Y") if isinstance(val, date) else val.strftime("%d/%m/%Y %H:%M")
    if isinstance(val, time):
        return val.strftime("%H:%M")
    if isinstance(val, bool):
        return "Sí" if val else "No"
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    if s.lower() in ("none", "null"):
        return ""
    if s.startswith("data:image/"):
        return "[firma digital]"
    return s


def _field_display_value(resultado, field):
    val = getattr(resultado, field.name, None)
    display_getter = f"get_{field.name}_display"
    if hasattr(resultado, display_getter):
        try:
            val = getattr(resultado, display_getter)()
        except (TypeError, ValueError):
            pass
    return _serialize_export_value(val)


def _export_resultado_tabla(resultado):
    """Serializa campos del modelo como lista JSON [{parametro, resultado}, ...]."""
    if not resultado:
        return ""
    rows = []
    for field in resultado._meta.fields:
        if field.name in _TABLA_SKIP_FIELDS:
            continue
        if field.name.endswith(_META_SKIP_SUFFIXES):
            continue
        if getattr(field, "is_relation", False):
            continue
        raw = getattr(resultado, field.name, None)
        if raw is None or raw == "":
            continue
        serialized = _field_display_value(resultado, field)
        if serialized == "":
            continue
        parametro = field.verbose_name or field.name.replace("_", " ").title()
        rows.append({"parametro": str(parametro), "resultado": serialized})
    return json.dumps(rows, ensure_ascii=False) if rows else ""


def _flatten_builder_fields(fields):
    for field in fields:
        if field.get("type") == "section":
            yield from _flatten_builder_fields(field.get("children") or [])
        else:
            yield field


def _export_form_builder_tabla(visita_examen):
    from .form_builder.schema import normalize_schema
    from .models import ExamenSubmission

    submission = (
        ExamenSubmission.objects.filter(visita_examen=visita_examen)
        .order_by("-id")
        .first()
    )
    if not submission or not submission.answers:
        return ""
    fields = normalize_schema(visita_examen.examen.campos)
    rows = []
    for field in _flatten_builder_fields(fields):
        field_id = str(field.get("id", ""))
        if not field_id:
            continue
        val = submission.answers.get(field_id)
        if val is None or val == "":
            continue
        rows.append(
            {
                "parametro": field.get("label") or field_id,
                "resultado": _serialize_export_value(val),
            }
        )
    return json.dumps(rows, ensure_ascii=False) if rows else ""


def get_export_config(examen_id):
    return EXPORT_FIELD_REGISTRY.get(int(examen_id), {})


def _resolve_field_value(resultado, field_name, aliases):
    """Obtiene valor del resultado probando nombre directo y alias."""
    if hasattr(resultado, field_name):
        val = getattr(resultado, field_name)
        if val is not None and val != "":
            return val
    for real_name, alias in aliases.items():
        if field_name == alias and hasattr(resultado, real_name):
            val = getattr(resultado, real_name, "")
            if val is not None and val != "":
                return val
    alias = aliases.get(field_name)
    if alias and hasattr(resultado, alias):
        return getattr(resultado, alias, "")
    return ""


def _export_child_tables(resultado, child_tables):
    """Serializa tablas hijas como JSON compacto por prefijo."""
    out = {}
    if not child_tables or not resultado:
        return out
    for rel_name, columns in child_tables.items():
        try:
            related = getattr(resultado, rel_name).all()
        except AttributeError:
            continue
        rows = []
        for row in related:
            rows.append({col: getattr(row, col, "") or "" for col in columns})
        if rows:
            out[rel_name] = json.dumps(rows, ensure_ascii=False)
    return out


def _export_form_builder(visita_examen):
    from .models import ExamenSubmission

    try:
        submission = ExamenSubmission.objects.filter(
            visita_examen=visita_examen
        ).order_by("-id").first()
    except Exception:
        submission = None
    if submission and submission.answers:
        return {"form_builder_answers": json.dumps(submission.answers, ensure_ascii=False)}
    return {}


def _export_seguimiento_sesiones(visita_examen):
    from .models import SeguimientoIntervencionesResult

    sesiones = SeguimientoIntervencionesResult.objects.filter(
        visita_examen=visita_examen
    ).order_by("numero_sesion")
    out = {}
    for s in sesiones:
        prefix = f"sesion_{s.numero_sesion}"
        out[f"{prefix}_fecha"] = s.fecha
        out[f"{prefix}_asistencia"] = s.asistencia
        out[f"{prefix}_observaciones"] = s.observaciones or ""
    return out


def extract_exam_export_data(visita_examen, campos_solicitados=None):
    """
    Devuelve dict campo → valor para un VisitaExamen completado.
    campos_solicitados: lista de nombres técnicos (puntaje_total, motivo_consulta, …)
    """
    examen_id = visita_examen.examen_id
    config = get_export_config(examen_id)
    aliases = config.get("aliases", {})
    data = {}

    if visita_examen.estado != "completado":
        for campo in campos_solicitados or []:
            data[campo] = ""
        return data

    meta_campos = {"estado_examen", "evaluador", "notas_visita", "resultados_tabla"}

    # Seguimiento intervenciones — múltiples sesiones
    if examen_id == 40:
        data.update(_export_seguimiento_sesiones(visita_examen))
        return data

    resultado = visita_examen.get_resultado_instance()
    if not resultado:
        data.update(_export_form_builder(visita_examen))
        tabla = _export_form_builder_tabla(visita_examen)
        if tabla:
            data["resultados_tabla"] = tabla
        return data

    fields = config.get("fields") or []
    if campos_solicitados:
        fields = [
            f for f in campos_solicitados
            if f not in meta_campos
        ]

    for field in fields:
        data[field] = _resolve_field_value(resultado, field, aliases)

    data.update(_export_child_tables(resultado, config.get("child_tables")))
    data.update(_export_form_builder(visita_examen))

    tabla = _export_resultado_tabla(resultado)
    if tabla:
        data["resultados_tabla"] = tabla

    # Campos genéricos solicitados no en registry
    if campos_solicitados:
        for campo in campos_solicitados:
            if campo in data:
                continue
            if campo == "resultados_tabla":
                continue
            if campo == "estado_examen":
                data[campo] = visita_examen.get_estado_display()
            elif campo == "evaluador":
                data[campo] = visita_examen.evaluador or ""
            elif campo == "notas_visita":
                data[campo] = visita_examen.visita.notas_aclaratorias or ""
            elif hasattr(resultado, campo):
                data[campo] = getattr(resultado, campo, "") or ""

    return data


def normalize_campo_examen(campo):
    """Mapea alias de UI (puntaje_total) al nombre real del modelo si aplica."""
    for _eid, cfg in EXPORT_FIELD_REGISTRY.items():
        aliases = cfg.get("aliases", {})
        for real, alias in aliases.items():
            if campo == alias or campo == "puntaje_total" and real in (
                "puntuacion_total",
                "puntuacion",
                "puntaje_total",
            ):
                return real
    return campo


def column_label(examen_nombre, campo):
    label = CAMPO_EXAMEN_LABELS.get(campo, campo.replace("_", " ").title())
    return f"{examen_nombre} - {label}"
