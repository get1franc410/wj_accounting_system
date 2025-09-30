# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\reporting\templatetags\custom_filters.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter  
def abs_value(value):
    """Return absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0
