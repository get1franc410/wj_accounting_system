# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\customers\api_views.py

from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import Customer
from decimal import Decimal # 👈 *** ADD THIS IMPORT ***

@login_required
@require_http_methods(["GET"])
def customer_search_api(request):
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 50))
    
    print(f"🔍 Customer search API called with query: '{query}', limit: {limit}")
    
    customers_qs = Customer.objects.filter(company=request.user.company)
    
    if query:
        print(f"🔍 Searching for customers matching '{query}'")
        customers = customers_qs.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )[:limit]
    elif request.GET.get('all') == '1':
        print(f"📋 Loading all customers because 'all=1' was passed.")
        customers = customers_qs.order_by('name')[:limit]
    else:
        customers = Customer.objects.none()

    results = []
    for customer in customers:
        # ======================================================================
        # START: MODIFICATION TO RESPECT ENTITY TYPE
        # ======================================================================
        receivable_to_show = customer.receivable_balance
        payable_to_show = customer.payable_balance

        if customer.entity_type == Customer.CUSTOMER:
            # A pure customer should not have a payable balance shown
            payable_to_show = Decimal('0.00')
        elif customer.entity_type == Customer.VENDOR:
            # A pure vendor should not have a receivable balance shown
            receivable_to_show = Decimal('0.00')
        # If type is 'both', we show both balances as they are from the database.

        results.append({
            'id': customer.id,
            'name': customer.name,
            'email': customer.email or '',
            'phone': customer.phone or '',
            'customer_type': customer.get_entity_type_display(),
            'receivable_balance': str(receivable_to_show), # Use the filtered value
            'payable_balance': str(payable_to_show),     # Use the filtered value
            'credit_limit': str(customer.credit_limit)
        })
        # ======================================================================
        # END: MODIFICATION
        # ======================================================================
    
    print(f"✅ Returning {len(results)} results")
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
        
        if Customer.objects.filter(name=name, company=request.user.company).exists():
            return JsonResponse({'success': False, 'error': 'Customer already exists'})
        
        # By default, a new entity via smart search is a 'Customer'
        customer = Customer.objects.create(
            name=name,
            company=request.user.company,
            entity_type=Customer.CUSTOMER 
        )
        
        return JsonResponse({
            'success': True,
            'item': {
                'id': customer.id,
                'name': customer.name,
                'email': customer.email or '',
                'phone': customer.phone or '',
                'customer_type': customer.get_entity_type_display(),
                'receivable_balance': '0.00', # Will be 0 on creation
                'payable_balance': '0.00',    # Will be 0 on creation
                'credit_limit': str(customer.credit_limit)
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def customer_filter_api(request):
    """Filter customers by transaction type compatibility"""
    transaction_type = request.GET.get('transaction_type', '')
    company = request.user.company
    
    customers = Customer.objects.filter(company=company)
    
    if transaction_type:
        if transaction_type in ['SALE', 'PAYMENT']:
            customers = customers.filter(entity_type__in=[Customer.CUSTOMER, Customer.BOTH])
        elif transaction_type in ['PURCHASE', 'EXPENSE']:
            customers = customers.filter(entity_type__in=[Customer.VENDOR, Customer.BOTH])
    
    results = []
    for customer in customers.order_by('name'):
        results.append({
            'id': customer.id,
            'name': customer.name,
            'entity_type': customer.get_entity_type_display(),
            'email': customer.email or '',
            'phone': customer.phone or ''
        })
    
    return JsonResponse({'customers': results})

