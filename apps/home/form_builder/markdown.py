# -*- coding: utf-8 -*-
"""Renderizado seguro de Markdown para bloques ``info`` del Form Builder."""
from __future__ import annotations

import bleach
import markdown

_ALLOWED_TAGS = frozenset({"p", "strong", "em", "ul", "ol", "li", "br"})
_ALLOWED_ATTRIBUTES: dict = {}


def render_safe_markdown(text: str) -> str:
    """Convierte Markdown básico a HTML y elimina etiquetas/atributos no permitidos."""
    if not text or not str(text).strip():
        return ""
    raw = markdown.markdown(
        str(text),
        extensions=["extra", "sane_lists"],
        output_format="html",
    )
    return bleach.clean(
        raw,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        strip=True,
    )
