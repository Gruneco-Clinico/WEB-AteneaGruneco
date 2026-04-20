# -*- coding: utf-8 -*-
import json

from django import template
from django.utils.html import escape

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
