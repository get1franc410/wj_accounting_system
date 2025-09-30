# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\api_views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from apps.customers.models import Customer
from apps.inventory.models import InventoryItem
from apps.transactions.models import Transaction
from apps.accounts.models import Account

@login_required
def customer_search(request):
    """Search customers for autocomplete"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    customers = Customer.objects.filter(
        company=request.user.company,
        entity_type__in=['customer', 'both']
    ).filter(
        Q(name__icontains=query) | Q(email__icontains=query)
    )[:10]
    
    results = [{
        'id': customer.id,
        'text': customer.name,
        'email': customer.email,
        'phone': customer.phone
    } for customer in customers]
    
    return JsonResponse({'results': results})

@login_required
def vendor_search(request):
    """Search vendors for autocomplete"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    vendors = Customer.objects.filter(
        company=request.user.company,
        entity_type__in=['vendor', 'both']
    ).filter(
        Q(name__icontains=query) | Q(email__icontains=query)
    )[:10]
    
    results = [{
        'id': vendor.id,
        'text': vendor.name,
        'email': vendor.email,
        'phone': vendor.phone
    } for vendor in vendors]
    
    return JsonResponse({'results': results})

@login_required
def inventory_search(request):
    """Search inventory items for autocomplete"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    items = InventoryItem.objects.filter(
        company=request.user.company
    ).filter(
        Q(name__icontains=query) | Q(sku__icontains=query)
    )[:10]
    
    results = [{
        'id': item.id,
        'text': f"{item.name} ({item.sku})",
        'sku': item.sku,
        'price': str(item.unit_price),
        'stock': item.quantity_on_hand
    } for item in items]
    
    return JsonResponse({'results': results})

@login_required
def account_search(request):
    """Search accounts for autocomplete"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    accounts = Account.objects.filter(
        company=request.user.company
    ).filter(
        Q(name__icontains=query) | Q(code__icontains=query)
    )[:10]
    
    results = [{
        'id': account.id,
        'text': f"{account.code} - {account.name}",
        'code': account.code,
        'type': account.account_type.name
    } for account in accounts]
    
    return JsonResponse({'results': results})

@login_required
def transaction_search(request):
    """Search transactions for autocomplete"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    transactions = Transaction.objects.filter(
        company=request.user.company
    ).filter(
        Q(description__icontains=query) | Q(reference__icontains=query)
    )[:10]
    
    results = [{
        'id': transaction.id,
        'text': f"{transaction.reference} - {transaction.description}",
        'reference': transaction.reference,
        'amount': str(transaction.amount),
        'date': transaction.date.strftime('%Y-%m-%d')
    } for transaction in transactions]
    
    return JsonResponse({'results': results})
