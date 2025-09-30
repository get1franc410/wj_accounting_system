# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\context_processors.py

from .utils import get_currency_symbol, get_currency_icon_class, format_currency

def currency_context(request):
    """
    Makes the company's currency symbol AND icon class available to all templates.
    """
    # Default values for anonymous users or companies without a currency set
    symbol = '₦'
    icon_class = 'fa-naira-sign'
    currency_code = 'NGN'

    # This 'if' block is the important part
    if (request.user.is_authenticated and 
        hasattr(request.user, 'company') and 
        request.user.company and
        hasattr(request.user.company, 'currency')):
        
        company = request.user.company
        currency_code = getattr(company, 'currency', 'NGN') 
        
        # Use centralized utility functions
        symbol = get_currency_symbol(currency_code)
        icon_class = get_currency_icon_class(currency_code)

    return {
        'currency_symbol': symbol,
        'currency_icon_class': icon_class,
        'currency_code': currency_code,
        'format_currency': lambda amount: format_currency(amount, currency_code),
    }