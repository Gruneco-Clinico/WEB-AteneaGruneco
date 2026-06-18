from django import template
import json
import re

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
