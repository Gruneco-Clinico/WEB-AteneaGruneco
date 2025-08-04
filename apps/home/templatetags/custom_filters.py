from django import template

register = template.Library()

@register.filter
def class_name(obj):
    """Retorna el nombre de la clase del objeto"""
    return obj.__class__.__name__