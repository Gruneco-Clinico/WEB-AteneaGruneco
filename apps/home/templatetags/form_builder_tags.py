# -*- coding: utf-8 -*-
import json

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from apps.home.form_builder.markdown import render_safe_markdown

register = template.Library()


@register.filter
def get_item(d, key):
    if d is None:
        return None
    if not hasattr(d, "get"):
        return None
    return d.get(key)


@register.filter
def contains_val(seq, arg):
    if not seq:
        return False
    if not isinstance(seq, (list, tuple)):
        return str(seq) == str(arg)
    arg_s = str(arg)
    return any(str(x) == arg_s for x in seq)


@register.simple_tag
def fb_input_name(prefix, fid):
    if prefix:
        return f"{prefix}{fid}"
    return str(fid)


@register.simple_tag
def fb_concat(*parts):
    return "".join(str(p) for p in parts)


@register.filter
def fb_attr_json(value):
    """Serializa a JSON y escapa para usar dentro de un atributo HTML."""
    if value is None:
        return ""
    return escape(json.dumps(value, default=str, ensure_ascii=False))


@register.filter
def fb_markdown(value):
    """Renderiza Markdown básico sanitizado para bloques ``info``."""
    return mark_safe(render_safe_markdown(value or ""))


def _field_type(f):
    if isinstance(f, dict):
        return (f.get("type") or "").strip()
    return (getattr(f, "type", "") or "").strip()


@register.filter
def fb_filter_sections(fields):
    """Devuelve solo los campos top-level cuyo type == 'section'."""
    if not fields:
        return []
    return [f for f in fields if _field_type(f) == "section"]


@register.filter
def fb_filter_non_sections(fields):
    """Devuelve solo los campos top-level cuyo type != 'section'."""
    if not fields:
        return []
    return [f for f in fields if _field_type(f) != "section"]
