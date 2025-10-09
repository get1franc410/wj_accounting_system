# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\inventory\api_views.py

from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import InventoryItem

@login_required
@require_http_methods(["GET"])
def inventory_search_api(request):
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 15))
    item_type_filter = request.GET.get('item_type', '').strip()  

    items = InventoryItem.objects.filter(company=request.user.company, is_active=True)

    if item_type_filter:
        items = items.filter(item_type=item_type_filter)

    if request.GET.get('all') != '1':
        items = items.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(description__icontains=query)
        )
    
    items = items[:limit]
    
    results = []
    for item in items:
        results.append({
            'id': item.id,
            'name': item.name,
            'sku': item.sku or '',
            'description': item.description or '',
            'unit_of_measurement': item.unit_of_measurement or 'pcs',
            'quantity_on_hand': str(item.quantity_on_hand),
            'sale_price': str(item.sale_price or 0),
            'purchase_price': str(item.purchase_price or 0),
            'item_type': item.item_type,
            'item_type_display': item.get_item_type_display()
        })
    
    return JsonResponse({'results': results})

@login_required
@require_http_methods(["GET"])
def inventory_item_detail_api(request, item_id):
    try:
        item = InventoryItem.objects.get(id=item_id, is_active=True)
        
        data = {
            'id': item.id,
            'name': item.name,
            'sku': item.sku or '',
            'description': item.description or '',
            'unit_of_measurement': item.unit_of_measurement or 'pcs',
            'quantity_on_hand': str(item.quantity_on_hand),
            'sale_price': str(item.sale_price or 0),
            'purchase_price': str(item.purchase_price or 0),
            'allow_fractional_quantities': getattr(item, 'allow_fractional_quantities', True),
            'enable_batch_tracking': getattr(item, 'enable_batch_tracking', False),
            'batches': [] 
        }
        
        return JsonResponse(data)
        
    except InventoryItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
