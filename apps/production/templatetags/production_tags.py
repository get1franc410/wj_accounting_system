# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\production\templatetags\production_tags.py
from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter
def mul(value, arg):
    """Safely multiply the value by the argument"""
    try:
        v = Decimal(str(value or '0'))
        a = Decimal(str(arg or '0'))
        return v * a
    except (ValueError, TypeError, InvalidOperation):
        return 0

@register.filter
def sub(value, arg):
    """Safely subtract the argument from the value"""
    try:
        v = Decimal(str(value or '0'))
        a = Decimal(str(arg or '0'))
        return v - a
    except (ValueError, TypeError, InvalidOperation):
        return 0

@register.filter
def add(value, arg):
    """Safely add the argument to the value"""
    try:
        v = Decimal(str(value or '0'))
        a = Decimal(str(arg or '0'))
        return v + a
    except (ValueError, TypeError, InvalidOperation):
        return 0

@register.filter
def div(value, arg):
    """Safely divide the value by the argument"""
    try:
        v = Decimal(str(value or '0'))
        a = Decimal(str(arg or '0'))
        if a == 0:
            return 0
        return v / a
    except (ValueError, TypeError, InvalidOperation):
        return 0
