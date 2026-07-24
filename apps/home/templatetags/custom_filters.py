from django import template
import json
import re
from datetime import date, datetime, time as time_cls

from django.utils.formats import date_format, time_format
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def class_name(obj):
    """Retorna el nombre de la clase del objeto"""
    return obj.__class__.__name__

@register.filter
def get_item(dictionary, key):
    """Accede a un diccionario con clave dinámica."""
    if not dictionary:
        return ""
    return dictionary.get(str(key), "")

@register.filter
def concat(value, arg):
    """Concatena strings en templates Django"""
    return f"{value}{arg}"

@register.filter
def mul(value, arg):
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0
    
@register.filter
def to_int(value):
    """
    Convierte un string como '3. Frecuentemente' en el número 3.
    Si ya es int, lo devuelve igual.
    """
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    match = re.match(r"(\d+)", str(value))
    return int(match.group(1)) if match else 0


@register.filter
def json_dumps(value):
    """Serializa a JSON seguro para atributos HTML (p. ej. data-examenes)."""
    if value is None:
        return "[]"
    return json.dumps(value, ensure_ascii=False)


@register.filter
def empty_dash(value):
    """None o vacío → guión; útil en PDF/impresión."""
    if value is None or value == "":
        return "—"
    return value


@register.filter
def exam_display_name(name):
    """Nombre técnico del examen → etiqueta legible."""
    if not name:
        return ""
    return str(name).replace("_", " ")


@register.filter
def render_exam_value(value):
    """Renderiza valores de examen: fechas legibles o firmas base64 como <img>."""
    if value is None or value == "":
        return mark_safe("")

    if isinstance(value, datetime):
        return mark_safe(escape(date_format(value, "DATETIME_FORMAT")))
    if isinstance(value, date):
        return mark_safe(escape(date_format(value, "DATE_FORMAT")))
    if isinstance(value, time_cls):
        return mark_safe(escape(time_format(value, "TIME_FORMAT")))

    s = str(value).strip()
    if s.lower() in ("none", "null"):
        return mark_safe("")

    if s.startswith("data:image/") and ";base64," in s:
        safe_src = s.replace('"', "%22")
        return mark_safe(
            f'<img src="{safe_src}" alt="Firma" class="hc-firma-img" />'
        )

    return mark_safe(escape(s))
