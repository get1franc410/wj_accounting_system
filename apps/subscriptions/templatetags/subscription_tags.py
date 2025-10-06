# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\templatetags\subscription_tags.py
from django import template
from apps.subscriptions.utils import has_production_access as check_production_access

register = template.Library()

@register.filter
def has_production_access(user):
    """Template filter to check if user has production access"""
    return check_production_access(user)
