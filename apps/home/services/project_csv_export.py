# -*- encoding: utf-8 -*-
"""
C-15: catálogo y extracción de campos para exportación CSV por examen.

Soporta resultados legacy (modelos) y builder (ExamenSubmission).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from django.db import models

from apps.home.exam_registry import EXAM_REGISTRY, get_exam_config, get_exam_model
from apps.home.form_builder.schema import normalize_schema

logger = logging.getLogger(__name__)

# Campos numéricos/interpretación que se tratan como "resumen" por defecto.
_SUMMARY_ATTRS = frozenset(
    {
        "puntaje_total",
        "puntuacion_total",
        "puntuacion",
        "interpretacion",
        "suma_cajas",
        "cdr_global",
        "cdr_interpretacion",
        "tipo_persona",
        "puntaje_autocuidado",
        "puntaje_cuidado_hogar",
        "puntaje_trabajo_recreacion",
        "puntaje_compras_dinero",
        "puntaje_viajes",
        "puntaje_comunicacion",
        "puntaje_tecnologia",
    }
)

_TECHNICAL_FIELDS = frozenset(
    {
        "id",
        "pk",
        "visita_examen",
        "created_at",
        "updated_at",
        "fecha_creacion",
        "fecha_actualizacion",
    }
)

# Exámenes de texto abierto: no se incluyen por defecto en la exportación.
_OPEN_TEXT_EXAM_IDS = frozenset({3, 4, 5, 7, 8, 9, 10, 12, 20, 38, 39, 40})

DEMOGRAPHIC_FIELDS: List[Tuple[str, str]] = [
    ("numero_documento", "Número de Documento"),
    ("tipo_documento", "Tipo de Documento"),
    ("celular", "Celular"),
    ("fecha_nacimiento", "Fecha de Nacimiento"),
    ("edad", "Edad"),
    ("genero", "Género"),
    ("municipio_nacimiento", "Municipio de Nacimiento"),
    ("departamento_nacimiento", "Departamento de Nacimiento"),
    ("pais_nacimiento", "País de Nacimiento"),
    ("estado_civil", "Estado Civil"),
    ("escolaridad", "Escolaridad"),
    ("ocupacion", "Ocupación"),
    ("lateralidad", "Lateralidad"),
    ("grupo_sanguineo", "Grupo Sanguíneo"),
    ("religion", "Religión"),
    ("eps", "EPS"),
    ("regimen", "Régimen"),
    ("direccion", "Dirección"),
    ("municipio_residencia", "Municipio de Residencia"),
    ("departamento_residencia", "Departamento de Residencia"),
    ("pais_residencia", "País de Residencia"),
    ("correo", "Correo Electrónico"),
]


@dataclass
class ExportField:
    key: str
    label: str
    group: str  # summary | item | table
    source: str  # legacy | builder
    attr: str = ""
    default_selected: bool = False
    table_columns: Tuple[str, ...] = ()


@dataclass
class ExamExportCatalog:
    examen_id: int
    examen_nombre: str
    fields: List[ExportField] = field(default_factory=list)
    default_selected: bool = False

    @property
    def summaries(self) -> List[ExportField]:
        return [f for f in self.fields if f.group == "summary"]

    @property
    def items(self) -> List[ExportField]:
        return [f for f in self.fields if f.group == "item"]

    @property
    def tables(self) -> List[ExportField]:
        return [f for f in self.fields if f.group == "table"]

    def field_by_key(self) -> Dict[str, ExportField]:
        return {f.key: f for f in self.fields}


def _is_seccion_evaluado(name: str) -> bool:
    return name.startswith("seccion_") and name.endswith("_evaluado")


def _legacy_summary_attrs(exam_id: int) -> List[str]:
    cfg = get_exam_config(exam_id) or {}
    export_cfg = cfg.get("export") or {}
    override = export_cfg.get("summary_fields")
    if override:
        return list(override)
    return []


def _legacy_table_specs(exam_id: int) -> List[dict]:
    cfg = get_exam_config(exam_id) or {}
    export_cfg = cfg.get("export") or {}
    return list(export_cfg.get("tables") or [])


def get_legacy_export_fields(examen) -> List[ExportField]:
    model = get_exam_model(examen.id)
    if model is None:
        return []

    override_summary = set(_legacy_summary_attrs(examen.id))
    fields: List[ExportField] = []
    seen_attrs = set()

    for django_field in model._meta.concrete_fields:
        name = django_field.name
        if name in _TECHNICAL_FIELDS or _is_seccion_evaluado(name):
            continue
        if isinstance(django_field, (models.ForeignKey, models.OneToOneField)):
            continue
        seen_attrs.add(name)
        label = str(django_field.verbose_name) if django_field.verbose_name else name
        is_summary = name in _SUMMARY_ATTRS or name in override_summary
        group = "summary" if is_summary else "item"
        fields.append(
            ExportField(
                key=f"{group}:{name}",
                label=label,
                group=group,
                source="legacy",
                attr=name,
                default_selected=is_summary,
            )
        )

    # Overrides que no existan como campos concretos (aliases virtuales)
    for name in override_summary:
        if name in seen_attrs:
            continue
        fields.insert(
            0,
            ExportField(
                key=f"summary:{name}",
                label=name.replace("_", " ").title(),
                group="summary",
                source="legacy",
                attr=name,
                default_selected=True,
            ),
        )

    for table in _legacy_table_specs(examen.id):
        related = table.get("related_name")
        if not related:
            continue
        label = table.get("label") or related
        columns = tuple(table.get("columns") or ())
        fields.append(
            ExportField(
                key=f"table:{related}",
                label=label,
                group="table",
                source="legacy",
                attr=related,
                default_selected=False,
                table_columns=columns,
            )
        )

    # Orden: summaries primero, luego items, luego tables
    order = {"summary": 0, "item": 1, "table": 2}
    fields.sort(key=lambda f: (order.get(f.group, 9), f.label.lower()))
    return fields


def _walk_builder_nodes(nodes: List[dict], out: List[ExportField]) -> None:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ntype = node.get("type") or "text"
        if ntype == "section":
            _walk_builder_nodes(normalize_schema(node.get("fields") or []), out)
            continue
        if ntype == "info":
            continue
        fid = node.get("id")
        if not fid:
            continue
        label = node.get("label") or fid
        if ntype == "computed":
            role = (node.get("export_role") or "total").lower()
            group = "summary" if role in ("total", "summary", "score") else "item"
            out.append(
                ExportField(
                    key=f"computed:{fid}",
                    label=label,
                    group=group,
                    source="builder",
                    attr=fid,
                    default_selected=group == "summary",
                )
            )
        elif ntype == "repeater":
            out.append(
                ExportField(
                    key=f"repeater:{fid}",
                    label=label,
                    group="table",
                    source="builder",
                    attr=fid,
                    default_selected=False,
                )
            )
        else:
            out.append(
                ExportField(
                    key=f"answer:{fid}",
                    label=label,
                    group="item",
                    source="builder",
                    attr=fid,
                    default_selected=False,
                )
            )


def get_builder_export_fields(examen) -> List[ExportField]:
    campos = getattr(examen, "campos", None)
    if not campos:
        return []
    out: List[ExportField] = []
    _walk_builder_nodes(normalize_schema(campos), out)
    order = {"summary": 0, "item": 1, "table": 2}
    out.sort(key=lambda f: (order.get(f.group, 9), f.label.lower()))
    return out


def build_exam_export_catalog(examenes: Iterable) -> List[ExamExportCatalog]:
    catalog: List[ExamExportCatalog] = []
    for examen in examenes:
        fields = get_legacy_export_fields(examen)
        if not fields:
            fields = get_builder_export_fields(examen)
        has_summary = any(f.group == "summary" for f in fields)
        open_text = int(examen.id) in _OPEN_TEXT_EXAM_IDS
        default_selected = has_summary and not open_text
        catalog.append(
            ExamExportCatalog(
                examen_id=int(examen.id),
                examen_nombre=examen.nombre,
                fields=fields,
                default_selected=default_selected,
            )
        )
    return catalog


def parse_export_selection(post, catalog: Sequence[ExamExportCatalog]) -> Dict[int, List[ExportField]]:
    """Valida tokens POST contra el catálogo. Soporta fallback global `campos_examen`."""
    by_id = {c.examen_id: c for c in catalog}
    selected_exam_ids = []
    for raw in post.getlist("examenes"):
        try:
            selected_exam_ids.append(int(raw))
        except (TypeError, ValueError):
            continue

    # Si no llega ningún examen, no exportar columnas de examen (UI nueva envía selección explícita).
    # Fallback antiguo: sin examenes ni campos_examen_<id> → usar catálogo completo con campos globales.
    has_namespaced = any(
        key.startswith("campos_examen_") for key in post.keys()
    )
    selection: Dict[int, List[ExportField]] = {}

    if has_namespaced:
        for exam_id in selected_exam_ids:
            cat = by_id.get(exam_id)
            if not cat:
                continue
            lookup = cat.field_by_key()
            chosen = []
            for token in post.getlist(f"campos_examen_{exam_id}"):
                spec = lookup.get(token)
                if spec:
                    chosen.append(spec)
            selection[exam_id] = chosen
        return selection

    # Fallback temporal: lista global campos_examen aplicada a todos los seleccionados
    global_tokens = post.getlist("campos_examen")
    exams = selected_exam_ids or list(by_id.keys())
    for exam_id in exams:
        cat = by_id.get(exam_id)
        if not cat:
            continue
        lookup = cat.field_by_key()
        # Mapear tokens antiguos (attr sin prefijo) a keys del catálogo
        chosen = []
        for token in global_tokens:
            if token in lookup:
                chosen.append(lookup[token])
                continue
            # token tipo "puntaje_total" → summary:puntaje_total o item:…
            for prefix in ("summary", "item", "table", "answer", "computed", "repeater"):
                key = f"{prefix}:{token}"
                if key in lookup:
                    chosen.append(lookup[key])
                    break
            else:
                # match por attr
                for spec in cat.fields:
                    if spec.attr == token:
                        chosen.append(spec)
                        break
        selection[exam_id] = chosen
    return selection


def serialize_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, (datetime, date)):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
    return str(value)


def serialize_table_json(rows: List[dict]) -> str:
    return json.dumps(rows, ensure_ascii=False, default=str, separators=(",", ":"))


def _legacy_attr_value(resultado, attr: str) -> Any:
    if attr == "puntaje_total":
        valor = getattr(resultado, "puntaje_total", None)
        if valor is None:
            valor = getattr(resultado, "puntuacion_total", None)
        if valor is None:
            valor = getattr(resultado, "puntuacion", None)
        return valor
    if attr == "suma_cajas" and hasattr(resultado, "calcular_suma_cajas"):
        try:
            return resultado.calcular_suma_cajas()
        except Exception:
            return getattr(resultado, "suma_cajas", None)
    if hasattr(resultado, f"get_{attr}_display"):
        try:
            display = getattr(resultado, f"get_{attr}_display")()
            if display not in (None, ""):
                return display
        except Exception:
            pass
    return getattr(resultado, attr, None)


def _serialize_related_table(resultado, related_name: str, columns: Sequence[str]) -> str:
    manager = getattr(resultado, related_name, None)
    if manager is None:
        return ""
    try:
        qs = manager.all() if hasattr(manager, "all") else manager
    except Exception:
        return ""
    rows = []
    for idx, obj in enumerate(qs, start=1):
        valores = []
        cols = columns or [
            f.name
            for f in obj._meta.concrete_fields
            if f.name not in _TECHNICAL_FIELDS
            and not isinstance(f, (models.ForeignKey, models.OneToOneField))
        ]
        for col in cols:
            if not hasattr(obj, col):
                continue
            field = obj._meta.get_field(col) if col in [f.name for f in obj._meta.fields] else None
            label = str(field.verbose_name) if field and field.verbose_name else col
            raw = _legacy_attr_value(obj, col)
            valores.append({"parametro": label, "resultado": serialize_csv_value(raw)})
        rows.append({"fila": idx, "valores": valores})
    if not rows:
        return ""
    return serialize_table_json(rows)


def _builder_repeater_json(answers: dict, attr: str, schema_nodes: List[dict]) -> str:
    raw = answers.get(attr)
    if not isinstance(raw, list):
        return ""
    # Buscar definición del repeater para etiquetas de subcampos
    sub_labels: Dict[str, str] = {}

    def _find(nodes):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if node.get("type") == "section":
                _find(normalize_schema(node.get("fields") or []))
            elif node.get("id") == attr and node.get("type") == "repeater":
                for sub in normalize_schema(node.get("fields") or []):
                    sid = sub.get("id")
                    if sid:
                        sub_labels[sid] = sub.get("label") or sid
                return

    _find(schema_nodes)
    rows = []
    for idx, row in enumerate(raw, start=1):
        if not isinstance(row, dict):
            continue
        valores = []
        for k, v in row.items():
            valores.append(
                {
                    "parametro": sub_labels.get(k, k),
                    "resultado": serialize_csv_value(v),
                }
            )
        rows.append({"fila": idx, "valores": valores})
    if not rows:
        return ""
    return serialize_table_json(rows)


def extract_exam_value(visita_examen, field_spec: ExportField) -> str:
    """Extrae y serializa un valor de un VisitaExamen según el ExportField."""
    try:
        if field_spec.source == "legacy":
            resultado = visita_examen.get_resultado_instance()
            if resultado is None:
                return ""
            if field_spec.group == "table":
                return _serialize_related_table(
                    resultado, field_spec.attr, field_spec.table_columns
                )
            valor = _legacy_attr_value(resultado, field_spec.attr)
            return serialize_csv_value(valor)

        # builder
        from apps.home.models import ExamenSubmission

        submission = (
            ExamenSubmission.objects.filter(visita_examen=visita_examen)
            .select_related("schema_version")
            .order_by("-id")
            .first()
        )
        if not submission:
            return ""
        answers = submission.answers or {}
        computed = submission.computed or {}
        schema_nodes = []
        if submission.schema_version_id and submission.schema_version:
            schema_nodes = normalize_schema(submission.schema_version.schema)
        else:
            schema_nodes = normalize_schema(getattr(visita_examen.examen, "campos", None))

        if field_spec.key.startswith("computed:"):
            return serialize_csv_value(computed.get(field_spec.attr))
        if field_spec.key.startswith("repeater:"):
            return _builder_repeater_json(answers, field_spec.attr, schema_nodes)
        return serialize_csv_value(answers.get(field_spec.attr))
    except Exception:
        logger.exception(
            "Error exportando campo %s de visita_examen %s",
            field_spec.key,
            getattr(visita_examen, "id", None),
        )
        return ""


def serialize_demographic_value(paciente, campo: str) -> str:
    valor = getattr(paciente, campo, None)
    display = getattr(paciente, f"get_{campo}_display", None)
    if callable(display):
        try:
            shown = display()
            if shown not in (None, ""):
                return serialize_csv_value(shown)
        except Exception:
            pass
    return serialize_csv_value(valor)


def build_csv_headers(
    demograficos: Sequence[str],
    selection: Dict[int, List[ExportField]],
    catalog: Sequence[ExamExportCatalog],
) -> List[str]:
    demo_labels = dict(DEMOGRAPHIC_FIELDS)
    headers = [
        "Código Proyecto",
        "Paciente",
        "Tipo de Visita",
        "Fecha Visita",
        "Estado Visita",
    ]
    for campo in demograficos:
        headers.append(demo_labels.get(campo, campo))
    by_id = {c.examen_id: c for c in catalog}
    for exam_id, fields in selection.items():
        cat = by_id.get(exam_id)
        nombre = cat.examen_nombre if cat else str(exam_id)
        for spec in fields:
            headers.append(f"{nombre} — {spec.label}")
    return headers
