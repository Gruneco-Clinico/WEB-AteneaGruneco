# -*- coding: utf-8 -*-
"""
Lenguaje de esquema para Examen.campos (lista de nodos).
Ver docs/analysis/FORM_BUILDER_INVENTORY.md
"""
import re
from typing import Any, Dict, List, Optional, Tuple


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
    expected = cond.get("equals")
    actual = answers.get(fid)
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


def parse_post_to_answers(fields: List[dict], post: dict) -> Tuple[dict, List[str]]:
    answers: Dict[str, Any] = {}
    errors: List[str] = []

    for node in fields:
        t = node.get("type", "text")
        if t in ("section", "computed", "repeater"):
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

    for node in fields:
        if node.get("type") != "repeater":
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

    for node in fields:
        t = node.get("type", "text")
        if t in ("section", "computed"):
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
                    if st == "section":
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

    return answers, errors


def apply_computed(fields: List[dict], answers: dict) -> dict:
    computed = {}
    for node in fields:
        if node.get("type") != "computed":
            continue
        cid = node.get("id")
        formula = node.get("formula", "")
        deps = node.get("depends_on") or []
        if formula == "imc" and cid:
            try:
                peso = answers.get(deps[0]) if len(deps) > 0 else answers.get("peso_kg")
                talla = answers.get(deps[1]) if len(deps) > 1 else answers.get("talla_cm")
                if peso is not None and talla not in (None, "", 0):
                    p = float(peso)
                    t_cm = float(talla)
                    if t_cm > 0:
                        t_m = t_cm / 100.0
                        computed[cid] = round(p / (t_m * t_m), 2)
            except (TypeError, ValueError, ZeroDivisionError):
                pass
    return computed


def validate_and_parse_post(
    schema: Any, post: dict
) -> Tuple[dict, dict, List[str]]:
    fields = normalize_schema(schema)
    answers, errors = parse_post_to_answers(fields, post)
    computed = apply_computed(fields, answers)
    return answers, computed, errors
