# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\transactions\api_views.py
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import Transaction, Customer

@login_required
@require_http_methods(["GET"])
def transaction_search_api(request):
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 15))
    
    if not query:
        return JsonResponse({'results': []})
    
    # Search transactions
    transactions = Transaction.objects.filter(
        company=request.user.company
    ).filter(
        Q(reference_number__icontains=query) |
        Q(description__icontains=query) |
        Q(customer__name__icontains=query)
    ).select_related('customer')[:limit]
    
    results = []
    for transaction in transactions:
        results.append({
            'id': transaction.id,
            'display_name': f"{transaction.reference_number or 'No Ref'} - {transaction.description[:50]}",
            'reference_number': transaction.reference_number or '',
            'description': transaction.description or '',
            'customer_name': transaction.customer.name if transaction.customer else '',
            'customer_id': transaction.customer.id if transaction.customer else None,
            'type': transaction.transaction_type,
            'amount': str(transaction.total_amount),
            'date': transaction.date.strftime('%Y-%m-%d')
        })
    
    return JsonResponse({'results': results})

@login_required
@require_http_methods(["GET"])
def smart_customer_search_api(request):
    """Smart customer search based on transaction type"""
    query = request.GET.get('q', '').strip()
    transaction_type = request.GET.get('transaction_type', '')
    limit = int(request.GET.get('limit', 15))
    
    company = request.user.company
    customers = Customer.objects.filter(company=company)
    
    # Filter by transaction type compatibility
    if transaction_type:
        if transaction_type in ['SALE', 'PAYMENT']:
            # Sales and payments - show customers and both
            customers = customers.filter(entity_type__in=[Customer.CUSTOMER, Customer.BOTH])
        elif transaction_type in ['PURCHASE', 'EXPENSE']:
            # Purchases and expenses - show vendors and both
            customers = customers.filter(entity_type__in=[Customer.VENDOR, Customer.BOTH])
    
    # Apply search filter
    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(company_name__icontains=query)
        )
    
    customers = customers[:limit]
    
    results = []
    for customer in customers:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'email': customer.email or '',
            'phone': customer.phone or '',
            'entity_type': customer.get_entity_type_display(),
            'receivable_balance': str(customer.receivable_balance),
            'payable_balance': str(customer.payable_balance),
            'is_compatible': True  # Already filtered above
        })
    
    return JsonResponse({'results': results})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def customer_create_api(request):
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'})
        
        # Check if customer already exists
        if Customer.objects.filter(name=name, company=request.user.company).exists():
            return JsonResponse({'success': False, 'error': 'Customer already exists'})
        
        # Create new customer
        customer = Customer.objects.create(
            name=name,
            company=request.user.company
        )
        
        return JsonResponse({
            'success': True,
            'item': {
                'id': customer.id,
                'name': customer.name,
                'email': customer.email or '',
                'phone': customer.phone or '',
                'company': getattr(customer, 'company_name', '') or '',
                'balance': str(customer.receivable_balance)
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["GET"])
def customer_detail_api(request):
    customer_id = request.GET.get('id')
    if not customer_id:
        return JsonResponse({'error': 'Customer ID required'}, status=400)
    
    try:
        customer = Customer.objects.get(id=customer_id, company=request.user.company)
        return JsonResponse({
            'item': {
                'id': customer.id,
                'name': customer.name,
                'email': customer.email or '',
                'phone': customer.phone or '',
                'company': getattr(customer, 'company_name', '') or '',
                'balance': str(customer.receivable_balance)
            }
        })
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)
