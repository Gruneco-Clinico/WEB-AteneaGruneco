# -*- coding: utf-8 -*-
"""
Lenguaje de esquema para Examen.campos (lista de nodos).
Ver docs/analysis/FORM_BUILDER_INVENTORY.md
"""
import re
from typing import Any, Dict, List, Optional, Tuple

_INFO_VARIANTS = frozenset({"info", "warning", "plain"})


def normalize_schema(raw: Any) -> List[dict]:
    if raw is None:
        return []
    if isinstance(raw, dict) and "fields" in raw:
        raw = raw["fields"]
    if not isinstance(raw, list):
        return []
    out = []
    for i, node in enumerate(raw):
        if not isinstance(node, dict):
            continue
        n = dict(node)
        t = n.get("type", "text")
        if t == "section":
            n.setdefault("label", n.get("id", f"Sección {i+1}"))
        elif t == "info":
            n.setdefault("label", "Instrucciones")
            n.setdefault("content", "")
            variant = (n.get("variant") or "plain").strip().lower()
            n["variant"] = variant if variant in _INFO_VARIANTS else "plain"
        else:
            n.setdefault("id", f"field_{i}")
        out.append(n)
    return out


def visible_when_match(node: dict, answers: dict) -> bool:
    cond = node.get("visible_when")
    if not cond:
        return True
    fid = cond.get("field")
    if not fid:
        return True
    op = (cond.get("op") or "equals").lower()
    expected = cond.get("equals")
    if "value" in cond:
        expected = cond["value"]
    actual = answers.get(fid)

    if op == "not_equals":
        if isinstance(expected, bool):
            return bool(actual) != expected
        return actual != expected
    if op == "contains":
        if actual is None:
            return False
        if isinstance(actual, (list, tuple)):
            exp_s = str(expected)
            return exp_s in [str(x) for x in actual]
        return str(expected) in str(actual)

    # equals (default)
    if isinstance(expected, bool):
        return bool(actual) == expected
    return actual == expected


def _parse_simple_value(node: dict, raw: Any) -> Any:
    t = node.get("type", "text")
    if t == "checkbox":
        if raw is None or raw == "":
            return False
        return raw in ("on", "true", "True", "1", True, 1)
    if t == "boolean":
        return raw in ("true", "True", "1", "on", True, 1)
    if t == "number":
        if raw is None or raw == "":
            return None
        try:
            v = float(str(raw).replace(",", "."))
            if v.is_integer():
                return int(v)
            return v
        except ValueError:
            return raw
    if t == "multiselect":
        if raw is None:
            return []
        if isinstance(raw, list):
            return [str(x) for x in raw if x not in (None, "")]
        return [str(raw)] if raw not in (None, "") else []
    if raw is None:
        return ""
    return str(raw).strip()


def _validate_leaf(node: dict, value: Any) -> Optional[str]:
    label = node.get("label", node.get("id", ""))
    t = node.get("type", "text")
    if node.get("required"):
        if value is None or value == "":
            return f"{label} es obligatorio"
        if t == "multiselect" and not value:
            return f"{label} es obligatorio"
    if t == "number" and value not in (None, ""):
        if not isinstance(value, (int, float)):
            return f"{label} debe ser numérico"
        if "min" in node and value < node["min"]:
            return f"{label} debe ser ≥ {node['min']}"
        if "max" in node and value > node["max"]:
            return f"{label} debe ser ≤ {node['max']}"
    return None


def _section_fields(node: dict) -> List[dict]:
    return normalize_schema(node.get("fields") or [])


def parse_post_to_answers(fields: List[dict], post: dict) -> Tuple[dict, List[str]]:
    answers: Dict[str, Any] = {}
    errors: List[str] = []

    def collect_simple(nodes: List[dict]) -> None:
        for node in nodes:
            t = node.get("type", "text")
            if t == "section":
                collect_simple(_section_fields(node))
                continue
            if t in ("repeater", "computed", "info"):
                continue
            fid = node.get("id")
            if not fid:
                continue
            if t == "multiselect":
                raw = post.getlist(fid) if hasattr(post, "getlist") else post.get(fid)
                if raw is None:
                    raw = []
                if not hasattr(post, "getlist") and not isinstance(raw, list):
                    raw = [raw] if raw not in (None, "") else []
            else:
                raw = post.get(fid) if hasattr(post, "get") else post.get(fid)
            answers[fid] = _parse_simple_value(node, raw)

    def collect_repeaters(nodes: List[dict]) -> None:
        for node in nodes:
            t = node.get("type", "text")
            if t == "section":
                collect_repeaters(_section_fields(node))
                continue
            if t != "repeater":
                continue
            rid = node.get("id")
            if not rid:
                continue
            subfields = normalize_schema(node.get("fields") or [])
            pattern = re.compile(rf"^{re.escape(rid)}__(\d+)__(.+)$")
            rows: Dict[int, Dict[str, Any]] = {}
            for pk in post.keys() if hasattr(post, "keys") else list(post.keys()):
                pk_s = str(pk)
                m = pattern.match(pk_s)
                if not m:
                    continue
                idx = int(m.group(1))
                subid = m.group(2)
                rows.setdefault(idx, {})
                subnode = next((s for s in subfields if s.get("id") == subid), None)
                if not subnode:
                    continue
                raw = post.get(pk) if hasattr(post, "get") else post[pk]
                if subnode.get("type") == "multiselect":
                    raw = (
                        post.getlist(pk)
                        if hasattr(post, "getlist")
                        else (raw if isinstance(raw, list) else [raw])
                    )
                rows[idx][subid] = _parse_simple_value(subnode, raw)
            answers[rid] = [rows[i] for i in sorted(rows.keys())] if rows else []

    def validate_nodes(nodes: List[dict]) -> None:
        for node in nodes:
            t = node.get("type", "text")
            if t == "section":
                if not visible_when_match(node, answers):
                    continue
                validate_nodes(_section_fields(node))
                continue
            if t in ("computed", "info"):
                continue
            if t == "repeater":
                rid = node.get("id")
                if not rid or not visible_when_match(node, answers):
                    continue
                subfields = normalize_schema(node.get("fields") or [])
                rows = answers.get(rid) or []
                if node.get("required") and not rows:
                    errors.append(
                        f"{node.get('label', rid)}: agregue al menos un ítem"
                    )
                for row in rows:
                    merged = {**answers, **row}
                    for sf in subfields:
                        st = sf.get("type", "text")
                        if st in ("section", "info"):
                            continue
                        sid = sf.get("id")
                        if not sid:
                            continue
                        if not visible_when_match(sf, merged):
                            continue
                        err = _validate_leaf(sf, row.get(sid))
                        if err:
                            errors.append(err)
                continue

            fid = node.get("id")
            if not fid:
                continue
            if not visible_when_match(node, answers):
                continue
            err = _validate_leaf(node, answers.get(fid))
            if err:
                errors.append(err)

    collect_simple(fields)
    collect_repeaters(fields)
    validate_nodes(fields)
    return answers, errors


def _safe_eval_arithmetic(formula: str, names: Dict[str, float]) -> Optional[float]:
    """Evalúa una expresión numérica simple usando solo nombres en ``names``."""
    if not formula or not formula.strip():
        return None
    allowed = set(names.keys())
    try:
        code_obj = compile(formula, "<formula>", "eval", flags=0)
    except SyntaxError:
        return None
    for item in code_obj.co_names:
        if item not in allowed:
            return None
    try:
        return float(eval(code_obj, {"__builtins__": {}}, dict(names)))
    except Exception:
        return None


def _resolve_numeric_dep(dep_id: str, answers: dict, computed: dict) -> Optional[float]:
    """Obtiene un valor numérico de ``answers`` o de calculados ya resueltos."""
    v = answers.get(dep_id)
    if v in (None, ""):
        v = computed.get(dep_id)
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _try_compute_node(
    node: dict, answers: dict, computed: dict
) -> Optional[Any]:
    cid = node.get("id")
    formula = (node.get("formula") or "").strip()
    deps = node.get("depends_on") or []
    prec = node.get("precision")
    if not cid or not formula:
        return None

    if formula == "imc":
        try:
            peso_key = deps[0] if len(deps) > 0 else "peso_kg"
            talla_key = deps[1] if len(deps) > 1 else "talla_cm"
            peso = _resolve_numeric_dep(peso_key, answers, computed)
            talla = _resolve_numeric_dep(talla_key, answers, computed)
            if peso is not None and talla not in (None, 0):
                t_m = talla / 100.0
                if t_m > 0:
                    return round(peso / (t_m * t_m), 2)
        except (TypeError, ValueError, ZeroDivisionError):
            pass
        return None

    ctx: Dict[str, float] = {}
    for d in deps:
        num = _resolve_numeric_dep(str(d), answers, computed)
        if num is None:
            return None
        ctx[str(d)] = num
    if not ctx:
        return None
    val = _safe_eval_arithmetic(formula, ctx)
    if val is None:
        return None
    if prec is not None:
        try:
            return round(val, int(prec))
        except (TypeError, ValueError):
            return val
    return val


def _collect_computed_nodes(fields: List[dict], acc: List[dict]) -> None:
    for node in fields:
        t = node.get("type", "text")
        if t == "section":
            _collect_computed_nodes(_section_fields(node), acc)
        elif t == "computed":
            acc.append(node)


def apply_computed(fields: List[dict], answers: dict) -> dict:
    """Calcula campos ``computed``, con soporte de encadenamiento entre ellos."""
    computed: Dict[str, Any] = {}
    nodes: List[dict] = []
    _collect_computed_nodes(fields, nodes)

    for _ in range(len(nodes) + 1):
        progress = False
        for node in nodes:
            cid = node.get("id")
            if not cid or cid in computed:
                continue
            result = _try_compute_node(node, answers, computed)
            if result is not None:
                computed[cid] = result
                progress = True
        if not progress:
            break
    return computed


def validate_and_parse_post(
    schema: Any, post: dict
) -> Tuple[dict, dict, List[str]]:
    fields = normalize_schema(schema)
    answers, errors = parse_post_to_answers(fields, post)
    computed = apply_computed(fields, answers)
    return answers, computed, errors
