from django import template

register = template.Library()

@register.filter
def get_value_or_empty(datos, campo):
    """Obtiene valor del diccionario o cadena vacía"""
    if datos and campo in datos and datos[campo] is not None:
        return datos[campo]
    return ''

@register.filter  
def is_checked(datos, campo):
    """Verifica si un checkbox debe estar marcado"""
    if datos and campo in datos:
        return 'checked' if datos[campo] else ''
    return ''

@register.filter
def is_selected(datos, campo, valor):
    """Verifica si una opción debe estar seleccionada"""
    if datos and campo in datos:
        return 'selected' if str(datos[campo]) == str(valor) else ''
    return ''

@register.filter
def to(value, arg):
    return range(value, int(arg) + 1)