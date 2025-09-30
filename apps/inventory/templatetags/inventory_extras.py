# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\inventory\templatetags\inventory_extras.py
from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
