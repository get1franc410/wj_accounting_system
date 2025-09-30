# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\templatetags\currency_filters.py
from django import template
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()

@register.filter
def currency(value, currency_code='NGN'):
    """
    Format a decimal value as currency with proper precision and thousands separator
    Usage: {{ amount|currency }} or {{ amount|currency:"USD" }}
    """
    if value is None or value == '':
        return '₦0.00'
    
    try:
        # Convert to Decimal for precise handling
        if isinstance(value, str):
            decimal_value = Decimal(value)
        else:
            decimal_value = Decimal(str(value))
        
        # Round to 2 decimal places using banker's rounding
        rounded_value = decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Get currency symbol
        from apps.core.utils import get_currency_symbol
        symbol = get_currency_symbol(currency_code)
        
        # Format with thousands separator
        if rounded_value >= 0:
            return f"{symbol}{intcomma(rounded_value)}"
        else:
            return f"-{symbol}{intcomma(abs(rounded_value))}"
            
    except (ValueError, TypeError, Exception):
        return '₦0.00'

@register.filter
def currency_no_symbol(value):
    """
    Format a decimal value without currency symbol
    Usage: {{ amount|currency_no_symbol }}
    """
    if value is None or value == '':
        return '0.00'
    
    try:
        if isinstance(value, str):
            decimal_value = Decimal(value)
        else:
            decimal_value = Decimal(str(value))
        
        rounded_value = decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return f"{intcomma(rounded_value)}"
        
    except (ValueError, TypeError, Exception):
        return '0.00'

@register.filter
def abs_currency(value, currency_code='NGN'):
    """
    Format absolute value as currency (always positive)
    Usage: {{ amount|abs_currency }}
    """
    if value is None or value == '':
        return '₦0.00'
    
    try:
        if isinstance(value, str):
            decimal_value = Decimal(value)
        else:
            decimal_value = Decimal(str(value))
        
        # Always use absolute value
        rounded_value = abs(decimal_value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        from apps.core.utils import get_currency_symbol
        symbol = get_currency_symbol(currency_code)
        
        return f"{symbol}{intcomma(rounded_value)}"
        
    except (ValueError, TypeError, Exception):
        return '₦0.00'

@register.filter
def percentage(value, decimal_places=2):
    """
    Format a decimal as percentage
    Usage: {{ 0.1547|percentage }} -> 15.47%
    """
    if value is None or value == '':
        return '0.00%'
    
    try:
        if isinstance(value, str):
            decimal_value = Decimal(value)
        else:
            decimal_value = Decimal(str(value))
        
        # Convert to percentage and round
        percentage_value = (decimal_value * 100).quantize(
            Decimal('0.' + '0' * decimal_places), 
            rounding=ROUND_HALF_UP
        )
        
        return f"{percentage_value}%"
        
    except (ValueError, TypeError, Exception):
        return '0.00%'

@register.simple_tag(takes_context=True)
def company_currency(context, value):
    """
    Format value using the current company's currency
    Usage: {% company_currency amount %}
    """
    request = context.get('request')
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        if hasattr(request.user, 'company') and request.user.company:
            currency_code = request.user.company.currency
            return currency(value, currency_code)
    
    return currency(value, 'NGN')  # Default to NGN
