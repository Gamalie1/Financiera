from django import template

register = template.Library()

# Filtro para acceder al valor de un diccionario
@register.filter
def get_item(dictionary, key):
    """Obtiene el valor de un diccionario por la clave"""
    return dictionary.get(key)