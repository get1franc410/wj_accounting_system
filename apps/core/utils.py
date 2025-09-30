# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\utils.py
"""
Core utility functions for the accounting system
"""
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.humanize.templatetags.humanize import intcomma

def get_currency_symbol(currency_code):
    """
    Get currency symbol for the given currency code.
    This is the single source of truth for currency symbols.
    """
    CURRENCY_SYMBOLS = {
        'NGN': '₦',
        'USD': '$',
        'GBP': '£',
        'CAD': 'C$',
        'EUR': '€',
    }
    return CURRENCY_SYMBOLS.get(currency_code, '₦')

def get_currency_icon_class(currency_code):
    """
    Get Font Awesome icon class for the given currency code.
    This is the single source of truth for currency icons.
    """
    CURRENCY_ICONS = {
        'NGN': 'fa-naira-sign',
        'USD': 'fa-dollar-sign',
        'GBP': 'fa-pound-sign',
        'CAD': 'fa-dollar-sign',
        'EUR': 'fa-euro-sign',
    }
    return CURRENCY_ICONS.get(currency_code, 'fa-money-bill-wave')

def format_currency(amount, currency_code='NGN', include_symbol=True):
    """
    Format amount with proper currency symbol and 2 decimal places
    """
    if amount is None or amount == '':
        return '₦0.00' if include_symbol else '0.00'
    
    try:
        # Convert to Decimal for precise handling
        if isinstance(amount, str):
            decimal_amount = Decimal(amount)
        else:
            decimal_amount = Decimal(str(amount))
        
        # Round to exactly 2 decimal places
        rounded_amount = decimal_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if include_symbol:
            symbol = get_currency_symbol(currency_code)
            if rounded_amount >= 0:
                return f"{symbol}{intcomma(rounded_amount)}"
            else:
                return f"-{symbol}{intcomma(abs(rounded_amount))}"
        else:
            return f"{intcomma(rounded_amount)}"
            
    except (ValueError, TypeError, Exception):
        return '₦0.00' if include_symbol else '0.00'

def safe_decimal(value, default='0.00'):
    """
    Safely convert any value to Decimal with 2 decimal places
    """
    if value is None or value == '':
        return Decimal(default)
    
    try:
        if isinstance(value, str):
            decimal_value = Decimal(value)
        else:
            decimal_value = Decimal(str(value))
        
        return decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
    except (ValueError, TypeError, Exception):
        return Decimal(default)

def get_supported_currencies():
    """
    Get list of all supported currencies
    """
    return [
        ('NGN', 'Nigerian Naira (₦)'),
        ('USD', 'US Dollar ($)'),
        ('GBP', 'British Pound (£)'),
        ('CAD', 'Canadian Dollar (C$)'),
        ('EUR', 'Euro (€)'),
    ]
