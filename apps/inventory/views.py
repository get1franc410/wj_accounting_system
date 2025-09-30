# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\inventory\views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from apps.reporting.export_utils import export_to_csv, export_to_excel, export_to_pdf
from datetime import date
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.db.models import Q, Sum, Count, F
from django.db import models
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.db import transaction
from django.urls import reverse
from apps.authentication.decorators import user_type_required, RoleRequiredMixin
from apps.authentication.models import User

from .models import InventoryItem, InventoryTransaction, InventoryBatch, InventoryMovement
from .forms import InventoryItemForm, InventoryTransactionForm, InventoryBatchForm, InventoryMovementForm, InventoryPriceAdjustmentForm

# --- FIX: Import the new utility function ---
from apps.journal.utils import create_journal_entry_for_inventory_transaction

# ===================================================================
# Enhanced Inventory ITEM Views (Master Data)
# ===================================================================
@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER, User.UserType.MANAGER, User.UserType.VIEWER]), name='dispatch')
class InventoryItemListView(ListView):
    model = InventoryItem
    template_name = 'inventory/inventory_item_list.html'
    context_object_name = 'items'
    paginate_by = 20
    ordering = ['name']

    def get_queryset(self):
        queryset = InventoryItem.objects.filter(company=self.request.user.company)
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(description__icontains=search_query)
            ).distinct()
        
        # Filter by item type
        item_type = self.request.GET.get('item_type', '')
        if item_type:
            queryset = queryset.filter(item_type=item_type)
        
        # Filter by stock status
        stock_status = self.request.GET.get('stock_status', '')
        if stock_status == 'low_stock':
            queryset = queryset.filter(quantity_on_hand__lte=models.F('reorder_level'))
        elif stock_status == 'out_of_stock':
            queryset = queryset.filter(quantity_on_hand=0)
        elif stock_status == 'in_stock':
            queryset = queryset.filter(quantity_on_hand__gt=0)
        elif stock_status == 'batch_tracked':
            queryset = queryset.filter(enable_batch_tracking=True)
        elif stock_status == 'expiry_tracked':
            queryset = queryset.filter(track_expiry=True)
            
        return queryset.select_related('asset_account', 'expense_account')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.request.user.company
        
        # Add filter values to context
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_item_type'] = self.request.GET.get('item_type', '')
        context['selected_stock_status'] = self.request.GET.get('stock_status', '')
        
        # Add choices for filters
        context['item_type_choices'] = InventoryItem.ITEM_TYPE_CHOICES
        
        # Enhanced summary statistics
        all_items = InventoryItem.objects.filter(company=company)
        context['total_items'] = all_items.count()
        context['low_stock_items'] = all_items.filter(
            quantity_on_hand__lte=models.F('reorder_level')
        ).count()
        context['out_of_stock_items'] = all_items.filter(quantity_on_hand=0).count()
        context['batch_tracked_items'] = all_items.filter(enable_batch_tracking=True).count()
        context['expiry_tracked_items'] = all_items.filter(track_expiry=True).count()
        
        # Calculate total inventory value using current average cost
        total_value = sum(
            item.quantity_on_hand * item.current_average_cost 
            for item in all_items
        )
        context['total_inventory_value'] = total_value
        
        # Get expiring items (if any)
        expiring_items = []
        for item in all_items.filter(track_expiry=True, enable_batch_tracking=True):
            expiring_batches = item.expiring_batches
            if expiring_batches.exists():
                expiring_items.append({
                    'item': item,
                    'batches': expiring_batches[:3]  # Show first 3 expiring batches
                })
        context['expiring_items'] = expiring_items[:5]  # Show top 5 items with expiring batches
        
        return context

def item_list(request):
    """Legacy function - redirects to class-based view"""
    return InventoryItemListView.as_view()(request)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER, User.UserType.MANAGER, User.UserType.VIEWER])
def item_detail(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk, company=request.user.company)
    transactions = InventoryTransaction.objects.filter(item=item).order_by('-transaction_date')
    
    # Get batch information if batch tracking is enabled
    batches = None
    expiring_batches = None
    if item.enable_batch_tracking:
        batches = item.batches.filter(quantity_remaining__gt=0).order_by('expiry_date', 'batch_number')
        if item.track_expiry:
            expiring_batches = item.expiring_batches
    
    # Get recent movements
    movements = InventoryMovement.objects.filter(item=item).order_by('-created_at')[:10]
    
    context = {
        'item': item,
        'transactions': transactions,
        'batches': batches,
        'expiring_batches': expiring_batches,
        'movements': movements,
    }
    return render(request, 'inventory/inventory_item_detail.html', context)


@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER])
def item_create(request):
    company = request.user.company
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, company=company)
        if form.is_valid():
            try:
                with transaction.atomic():
                    item = form.save(commit=False) 
                    item.company = company
                    item.save()
                    
                    # Create initial cost layer if initial purchase price is provided
                    initial_price = form.cleaned_data.get('initial_purchase_price')
                    if initial_price and initial_price > 0:
                        if item.enable_batch_tracking:
                            # Create initial batch
                            InventoryBatch.objects.create(
                                item=item,
                                batch_number="INITIAL-001",
                                quantity_remaining=0,  # No initial quantity, will be added via transactions
                                unit_cost=initial_price,
                                notes="Initial setup batch"
                            )
                        else:
                            # Create cost layer
                            from .models import InventoryCostLayer
                            InventoryCostLayer.objects.create(
                                item=item,
                                purchase_date=timezone.now(),
                                quantity=0,  # No initial quantity, will be added via transactions
                                quantity_remaining=0,
                                unit_cost=initial_price,
                                reference="Initial Setup"
                            )
                    
                    messages.success(request, f"Item '{item.name}' was created successfully.")
                    return redirect('inventory:item_list')
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
    else:
        form = InventoryItemForm(company=company)
    
    context = {
        'form': form,
        'page_title': 'Create New Inventory Item'
    }
    return render(request, 'inventory/inventory_item_form.html', context)


@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER])
def item_update(request, pk):
    company = request.user.company
    item = get_object_or_404(InventoryItem, pk=pk, company=company)
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, instance=item, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Item '{item.name}' was updated successfully.")
            return redirect('inventory:item_list')
    else:
        form = InventoryItemForm(instance=item, company=company)
    context = {
        'form': form,
        'item': item,
        'page_title': f'Edit Item: {item.name}'
    }
    return render(request, 'inventory/inventory_item_form.html', context)


# ===================================================================
# Enhanced Inventory TRANSACTION View (Stock Movements)
# ===================================================================
@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER]), name='dispatch')
class InventoryTransactionCreateView(View):
    form_class = InventoryTransactionForm
    template_name = 'inventory/inventory_transaction_form.html'

    def get(self, request, *args, **kwargs):
        initial_data = {}
        item_id = request.GET.get('item')
        if item_id:
            initial_data['item'] = item_id
        
        form = self.form_class(company=request.user.company, initial=initial_data)
        context = {
            'form': form,
            'page_title': 'New Inventory Transaction'
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, company=request.user.company)
        if form.is_valid():
            try:
                with transaction.atomic():
                    inventory_transaction = form.save(commit=False)
                    inventory_transaction.company = request.user.company
                    inventory_transaction.save()

                    item = inventory_transaction.item
                    quantity_change = inventory_transaction.get_quantity_change()
                    item.quantity_on_hand += quantity_change
                    item.save(update_fields=['quantity_on_hand'])
                    
                    # --- FIX: Call the utility function to create the journal entry ---
                    create_journal_entry_for_inventory_transaction(inventory_transaction)

                messages.success(request, f"Transaction recorded for {item.name} and journal entry created.")
                return redirect('inventory:item_detail', pk=item.pk)

            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
        
        context = {
            'form': form,
            'page_title': 'New Inventory Transaction'
        }
        return render(request, self.template_name, context)


# ===================================================================
# NEW: Inventory Movement Views
# ===================================================================
@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER, User.UserType.MANAGER, User.UserType.VIEWER])
def inventory_movement_list(request):
    """List all inventory movements - FIXED VERSION"""
    company = request.user.company
    
    # 🎯 GET ALL MOVEMENTS FOR THE COMPANY
    movements = InventoryMovement.objects.filter(company=company).select_related(
        'item', 'batch', 'created_by'
    ).order_by('-created_at')
    
    # Filter by processing status
    status_filter = request.GET.get('status', '')
    if status_filter == 'processed':
        movements = movements.filter(is_processed=True)
    elif status_filter == 'pending':
        movements = movements.filter(is_processed=False)
    
    # 🆕 ADD SEARCH FUNCTIONALITY
    search_query = request.GET.get('search', '')
    if search_query:
        movements = movements.filter(
            Q(item__name__icontains=search_query) |
            Q(reference_document__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # 🆕 ADD ITEM FILTER
    item_filter = request.GET.get('item')
    if item_filter:
        movements = movements.filter(item_id=item_filter)
    
    # Pagination
    paginator = Paginator(movements, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 🆕 ADD SUMMARY STATISTICS
    total_movements = movements.count()
    processed_count = movements.filter(is_processed=True).count()
    pending_count = movements.filter(is_processed=False).count()
    
    context = {
        'movements': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'item_filter': item_filter,
        'total_movements': total_movements,
        'processed_count': processed_count,
        'pending_count': pending_count,
        'page_title': 'Inventory Movements',
        # 🆕 ADD ITEMS FOR FILTER DROPDOWN
        'items': InventoryItem.objects.filter(company=company).order_by('name')
    }
    return render(request, 'inventory/inventory_movement_list.html', context)


@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER])
def inventory_movement_create(request):
    """Create new inventory movement - ENHANCED VERSION"""
    company = request.user.company
    
    # Get initial data from URL parameters
    initial_data = {}
    item_id = request.GET.get('item')
    if item_id:
        try:
            item = InventoryItem.objects.get(pk=item_id, company=company)
            initial_data['item'] = item_id
        except InventoryItem.DoesNotExist:
            messages.warning(request, "Selected item not found.")
    
    if request.method == 'POST':
        form = InventoryMovementForm(request.POST, company=company)
        if form.is_valid():
            try:
                with transaction.atomic():
                    movement = form.save(commit=False)
                    movement.company = company
                    movement.created_by = request.user
                    movement.save()
                    
                    # 🎯 PROCESS THE MOVEMENT IMMEDIATELY
                    try:
                        movement.process_movement()
                        messages.success(
                            request, 
                            f"✅ Movement processed successfully for {movement.item.name}. "
                            f"Stock {'increased' if movement.movement_type == 'IN' else 'decreased'} by {movement.quantity}."
                        )
                    except Exception as process_error:
                        messages.error(request, f"Movement created but processing failed: {process_error}")
                    
                    # Smart redirect
                    if item_id:
                        return redirect('inventory:item_detail', pk=movement.item.pk)
                    else:
                        return redirect('inventory:movement_list')
                        
            except Exception as e:
                messages.error(request, f"An error occurred while creating movement: {e}")
    else:
        form = InventoryMovementForm(company=company, initial=initial_data)
    
    context = {
        'form': form,
        'page_title': 'Create Inventory Movement',
        'selected_item': initial_data.get('item')
    }
    return render(request, 'inventory/inventory_movement_form.html', context)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER])
def export_inventory_movements(request):
    """Export inventory movements in requested format"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    movements = InventoryMovement.objects.filter(company=company).select_related(
        'item', 'batch', 'created_by'
    ).order_by('-created_at')
    
    headers = [
        'Date', 'Item Name', 'SKU', 'Movement Type', 'Reason', 'Custom Reason',
        'Quantity', 'Fair Market Value', 'Total Value', 'Batch Number', 
        'Reference Document', 'Created By', 'Status', 'Processed Date', 'Notes'
    ]
    
    data = []
    for movement in movements:
        total_value = ''
        if movement.fair_market_value:
            total_value = float(movement.quantity * movement.fair_market_value)
        
        row = [
            movement.created_at.strftime('%Y-%m-%d %H:%M'),
            movement.item.name,
            movement.item.sku or '',
            movement.get_movement_type_display(),
            movement.get_reason_display(),
            movement.custom_reason or '',
            float(movement.quantity),
            float(movement.fair_market_value) if movement.fair_market_value else '',
            total_value,
            movement.batch.batch_number if movement.batch else '',
            movement.reference_document or '',
            movement.created_by.get_full_name() if movement.created_by else '',
            'Processed' if movement.is_processed else 'Pending',
            movement.processed_at.strftime('%Y-%m-%d %H:%M') if movement.processed_at else '',
            movement.notes or ''
        ]
        data.append(row)
    
    filename = f"inventory_movements_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Inventory Movements"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Inventory Movements", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)
    
# ===================================================================
# Enhanced API Endpoints
# ===================================================================
@login_required
def get_item_details(request, pk):
    """
    Enhanced API endpoint that returns comprehensive item details
    including batch information and smart selection data
    """
    try:
        item = get_object_or_404(InventoryItem, pk=pk, company=request.user.company)
        
        # Get available batches if batch tracking is enabled
        batches = []
        if item.enable_batch_tracking:
            for batch in item.batches.filter(quantity_remaining__gt=0):
                batches.append({
                    'id': batch.id,
                    'batch_number': batch.batch_number,
                    'quantity_remaining': str(batch.quantity_remaining),
                    'unit_cost': str(batch.unit_cost),
                    'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                    'is_expiring_soon': batch.is_expiring_soon,
                    'days_to_expiry': batch.days_to_expiry
                })
        
        data = {
            'sale_price': str(item.sale_price),
            'purchase_price': str(item.current_average_cost),
            'description': item.description or '',
            'unit_of_measurement': item.unit_of_measurement,
            'unit_category': item.unit_category,
            'quantity_on_hand': str(item.quantity_on_hand),
            'is_product': item.item_type == InventoryItem.PRODUCT,
            'costing_method': item.get_costing_method_display(),
            'enable_batch_tracking': item.enable_batch_tracking,
            'allow_fractional_quantities': item.allow_fractional_quantities,
            'track_expiry': item.track_expiry,
            'is_low_on_stock': item.is_low_on_stock,
            'batches': batches,
            'reorder_level': str(item.reorder_level),
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_batch_details(request, item_id):
    """Get batches for a specific item"""
    try:
        item = get_object_or_404(InventoryItem, pk=item_id, company=request.user.company)
        
        if not item.enable_batch_tracking:
            return JsonResponse({'batches': []})
        
        batches = []
        for batch in item.batches.filter(quantity_remaining__gt=0).order_by('expiry_date', 'batch_number'):
            batches.append({
                'id': batch.id,
                'batch_number': batch.batch_number,
                'quantity_remaining': str(batch.quantity_remaining),
                'unit_cost': str(batch.unit_cost),
                'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                'manufacture_date': batch.manufacture_date.isoformat() if batch.manufacture_date else None,
                'supplier': batch.supplier,
                'is_expiring_soon': batch.is_expiring_soon,
                'is_expired': batch.is_expired,
                'days_to_expiry': batch.days_to_expiry,
                'display_text': f"{batch.batch_number} (Qty: {batch.quantity_remaining}, Cost: {batch.unit_cost})"
            })
        
        return JsonResponse({'batches': batches})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


@login_required 
def validate_quantity(request, item_id):
    """Validate quantity for fractional control"""
    try:
        item = get_object_or_404(InventoryItem, pk=item_id, company=request.user.company)
        quantity = float(request.GET.get('quantity', 0))
        batch_id = request.GET.get('batch_id')
        
        errors = []
        
        # Check fractional quantities
        if not item.allow_fractional_quantities and quantity % 1 != 0:
            errors.append(f"Item '{item.name}' only allows whole number quantities.")
        
        # Check batch availability
        if item.enable_batch_tracking and batch_id:
            try:
                batch = InventoryBatch.objects.get(id=batch_id, item=item)
                if batch.quantity_remaining < quantity:
                    errors.append(f"Insufficient quantity in batch {batch.batch_number}. Available: {batch.quantity_remaining}")
            except InventoryBatch.DoesNotExist:
                errors.append("Selected batch not found.")
        elif not item.enable_batch_tracking:
            # Check overall stock
            if item.quantity_on_hand < quantity:
                errors.append(f"Insufficient stock. Available: {item.quantity_on_hand}")
        
        return JsonResponse({
            'valid': len(errors) == 0,
            'errors': errors,
            'available_quantity': str(item.quantity_on_hand)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ===================================================================
# Enhanced Export Views
# ===================================================================
@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER])
def export_inventory_items(request):
    """Export inventory items with enhanced data - FIXED VERSION"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    items = InventoryItem.objects.filter(company=company).select_related(
        'income_account', 'expense_account', 'asset_account'
    ).order_by('name')
    
    # ✅ CORRECTED HEADERS - using actual model fields
    headers = [
        'Name', 'SKU', 'Item Type', 'Unit', 'Description',
        'Current Average Cost', 'Sale Price', 'Current Stock', 'Reorder Level', 
        'Costing Method', 'Batch Tracking', 'Fractional Quantities', 'Expiry Tracking',
        'Low Stock Status', 'Asset Account', 'Expense Account', 'Income Account', 'Total Value'
    ]
    
    # ✅ CORRECTED DATA - using actual model fields and methods
    data = []
    for item in items:
        try:
            row = [
                item.name,
                item.sku or '',
                item.get_item_type_display(),
                item.get_unit_of_measurement_display(),
                item.description or '',
                float(item.current_average_cost),  # This is a property method
                float(item.sale_price),
                float(item.quantity_on_hand),
                float(item.reorder_level),
                item.get_costing_method_display(),
                'Yes' if item.enable_batch_tracking else 'No',
                'Yes' if item.allow_fractional_quantities else 'No',
                'Yes' if item.track_expiry else 'No',
                'Yes' if item.is_low_on_stock else 'No',  # This is a property method
                f"{item.asset_account.account_number} - {item.asset_account.name}" if item.asset_account else '',
                f"{item.expense_account.account_number} - {item.expense_account.name}" if item.expense_account else '',
                f"{item.income_account.account_number} - {item.income_account.name}" if item.income_account else '',
                float(item.quantity_on_hand * item.current_average_cost),
            ]
            data.append(row)
        except Exception as e:
            # Skip problematic items but log the error
            print(f"Error processing item {item.name}: {e}")
            continue
    
    filename = f"inventory_items_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Inventory Items"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Inventory Items", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)


def export_inventory_transactions(request):
    """Export inventory transactions in requested format"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    transactions = InventoryTransaction.objects.filter(company=company).order_by('-transaction_date')
    
    headers = ['Date', 'Item', 'Transaction Type', 'Quantity', 'Unit Cost', 'Total Cost', 'Notes']
    data = []
    
    for txn in transactions:
        data.append([
            txn.transaction_date.date() if hasattr(txn.transaction_date, 'date') else txn.transaction_date,
            txn.item.name,
            txn.get_transaction_type_display(),
            txn.quantity,
            txn.unit_cost or 0,
            txn.total_cost or 0,
            txn.notes or ''
        ])
    
    filename = f"inventory_transactions_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Inventory Transactions"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Inventory Transactions", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)


def export_inventory_valuation(request):
    """Export inventory valuation report"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    items = InventoryItem.objects.filter(company=company).order_by('name')
    
    headers = ['Item Name', 'SKU', 'Current Stock', 'Average Unit Cost', 'Total Value', 'Reorder Level', 'Status']
    data = []
    total_inventory_value = 0
    
    for item in items:
        avg_cost = item.current_average_cost
        total_value = item.quantity_on_hand * avg_cost
        total_inventory_value += total_value
        
        status = 'Low Stock' if item.quantity_on_hand <= item.reorder_level else 'In Stock'
        if item.quantity_on_hand == 0:
            status = 'Out of Stock'
        
        data.append([
            item.name,
            item.sku or '',
            item.quantity_on_hand,
            avg_cost,
            total_value,
            item.reorder_level,
            status
        ])
    
    # Add summary
    data.append(['', '', '', '', '', '', ''])
    data.append(['TOTAL INVENTORY VALUE', '', '', '', total_inventory_value, '', ''])
    
    filename = f"inventory_valuation_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Inventory Valuation Report"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Inventory Valuation", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)
    

# ===================================================================
# Batch Management Views
# ===================================================================
@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER])
def batch_list(request, item_id):
    """List all batches for a specific item"""
    item = get_object_or_404(InventoryItem, pk=item_id, company=request.user.company)
    
    if not item.enable_batch_tracking:
        messages.error(request, "This item does not have batch tracking enabled.")
        return redirect('inventory:item_detail', pk=item_id)
    
    batches = item.batches.all().order_by('expiry_date', 'batch_number')
    
    context = {
        'item': item,
        'batches': batches,
        'page_title': f'Batches for {item.name}'
    }
    return render(request, 'inventory/batch_list.html', context)


@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER])
def batch_create(request, item_id):
    """Create new batch for an item"""
    item = get_object_or_404(InventoryItem, pk=item_id, company=request.user.company)
    
    if not item.enable_batch_tracking:
        messages.error(request, "This item does not have batch tracking enabled.")
        return redirect('inventory:item_detail', pk=item_id)
    
    if request.method == 'POST':
        form = InventoryBatchForm(request.POST)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.item = item
            batch.quantity_remaining = 0  # Will be updated via inventory transactions
            batch.unit_cost = item.current_average_cost or 0
            batch.save()
            
            messages.success(request, f"Batch '{batch.batch_number}' created successfully.")
            return redirect('inventory:batch_list', item_id=item.id)
    else:
        form = InventoryBatchForm()
    
    context = {
        'form': form,
        'item': item,
        'page_title': f'Create Batch for {item.name}'
    }
    return render(request, 'inventory/batch_form.html', context)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT])
def price_adjustment_create(request, item_id):
    """Create price adjustment for an item"""
    item = get_object_or_404(InventoryItem, pk=item_id, company=request.user.company)
    
    if item.costing_method != InventoryItem.CostingMethod.PRICE_ADJUSTMENT:
        messages.error(request, "Price adjustments are only available for items using 'Price Adjustment' costing method.")
        return redirect('inventory:item_detail', pk=item_id)
    
    if request.method == 'POST':
        form = InventoryPriceAdjustmentForm(request.POST, item=item)
        if form.is_valid():
            try:
                with transaction.atomic():
                    adjustment = form.save(commit=False)
                    adjustment.item = item
                    adjustment.old_unit_cost = item.current_average_cost
                    adjustment.created_by = request.user
                    adjustment.save()
                    
                    # Create journal entry for the adjustment
                    create_price_adjustment_journal_entry(adjustment)
                    
                    messages.success(request, f"Price adjustment created for {item.name}")
                    return redirect('inventory:item_detail', pk=item.id)
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
    else:
        form = InventoryPriceAdjustmentForm(item=item)
    
    context = {
        'form': form,
        'item': item,
        'page_title': f'Price Adjustment for {item.name}'
    }
    return render(request, 'inventory/price_adjustment_form.html', context)

def create_price_adjustment_journal_entry(adjustment):
    """Create journal entry for price adjustment"""
    from apps.journal.models import JournalEntry, JournalEntryLine
    from apps.accounts.models import Account, AccountType

    adjustment_amount = adjustment.adjustment_amount
    if adjustment_amount == 0:
        return
    
    company = adjustment.item.company
    description_text = f"Price adjustment for {adjustment.item.name} (Ref: PA-{adjustment.id})"

    journal_entry = JournalEntry.objects.create(
        company=company,
        date=adjustment.adjustment_date.date(),
        description=description_text,
        created_by=adjustment.created_by
    )

    if adjustment_amount > 0:  # Price increase
        # Debit Inventory Asset
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=adjustment.item.asset_account,
            description=f"Price adjustment increase - {adjustment.item.name}",
            debit=adjustment_amount,
            credit=0
        )
        
        # Credit Price Adjustment Income
        try:
            adjustment_account = Account.objects.get(
                company=company,
                name__iexact='Price Adjustment Income'
            )
        except Account.DoesNotExist:
            # --- DEFINITIVE FIX ---
            # AccountType is global, so we don't filter by company.
            revenue_type = AccountType.objects.get(name='Revenue')
            adjustment_account = Account.objects.create(
                company=company,
                account_type=revenue_type,
                name='Price Adjustment Income',
                account_number='4950',
                description='Income from inventory price adjustments'
            )
        
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=adjustment_account,
            description=f"Price adjustment increase - {adjustment.item.name}",
            debit=0,
            credit=adjustment_amount
        )
    
    else:  # Price decrease
        # Credit Inventory Asset
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=adjustment.item.asset_account,
            description=f"Price adjustment decrease - {adjustment.item.name}",
            debit=0,
            credit=abs(adjustment_amount)
        )
        
        # Debit Price Adjustment Expense
        try:
            adjustment_account = Account.objects.get(
                company=company,
                name__iexact='Price Adjustment Expense'
            )
        except Account.DoesNotExist:
            # --- DEFINITIVE FIX ---
            # AccountType is global, so we don't filter by company.
            expense_type = AccountType.objects.get(name='Expense')
            adjustment_account = Account.objects.create(
                company=company,
                account_type=expense_type,
                name='Price Adjustment Expense',
                account_number='6950',
                description='Expense from inventory price adjustments'
            )
        
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=adjustment_account,
            description=f"Price adjustment decrease - {adjustment.item.name}",
            debit=abs(adjustment_amount),
            credit=0
        )