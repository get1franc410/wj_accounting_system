# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\production\views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Q, Sum, F
from django.core.paginator import Paginator
from decimal import Decimal

from apps.authentication.decorators import user_type_required, RoleRequiredMixin
from apps.authentication.models import User
from apps.inventory.models import InventoryTransaction, InventoryItem, InventoryBatch
from apps.journal.models import JournalEntry, JournalEntryLine
from apps.accounts.models import Account

from .models import (
    ProductionFormula, FormulaIngredient, ProductionOrder, 
    MaterialUsage, ProductionWaste
)
from .forms import (
    ProductionFormulaForm, FormulaIngredientFormSet,
    ProductionOrderForm, ProductionOrderExecuteForm, MaterialUsageFormSet
)
from apps.subscriptions.utils import has_production_access


@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.STOCK_KEEPER]), name='dispatch')
class ProductionFormulaListView(View):
    def get(self, request):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        formulas = ProductionFormula.objects.filter(company=company)
        
        search_query = request.GET.get('search', '')
        if search_query:
            formulas = formulas.filter(
                Q(name__icontains=search_query) |
                Q(finished_product__name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        status_filter = request.GET.get('status', '')
        if status_filter == 'active':
            formulas = formulas.filter(is_active=True)
        elif status_filter == 'inactive':
            formulas = formulas.filter(is_active=False)
        
        paginator = Paginator(formulas.order_by('name'), 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'formulas': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
            'page_title': 'Production Formulas'
        }
        return render(request, 'production/formula_list.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER]), name='dispatch')
class ProductionFormulaCreateView(View):
    def get(self, request):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        form = ProductionFormulaForm(company=company)
        formset = FormulaIngredientFormSet(
            queryset=FormulaIngredient.objects.none(),
            form_kwargs={'company': company}
        )
        
        context = {
            'form': form,
            'formset': formset,
            'page_title': 'Create Production Formula'
        }
        return render(request, 'production/formula_form.html', context)
    
    def post(self, request):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        form = ProductionFormulaForm(request.POST, company=company)
        formset = FormulaIngredientFormSet(
            request.POST,
            form_kwargs={'company': company}
        )
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    formula = form.save(commit=False)
                    formula.company = company
                    formula.created_by = request.user
                    formula.save()
                    
                    formset.instance = formula
                    formset.save()
                    
                    messages.success(request, f"Production formula '{formula.name}' created successfully!")
                    return redirect('production:formula_list')
            except Exception as e:
                messages.error(request, f"Error creating formula: {e}")
        
        context = {
            'form': form,
            'formset': formset,
            'page_title': 'Create Production Formula'
        }
        return render(request, 'production/formula_form.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER]), name='dispatch')
class ProductionFormulaUpdateView(View):
    def get(self, request, pk):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        formula = get_object_or_404(ProductionFormula, pk=pk, company=company)
        
        form = ProductionFormulaForm(instance=formula, company=company)
        formset = FormulaIngredientFormSet(
            instance=formula,
            form_kwargs={'company': company}
        )
        
        context = {
            'form': form,
            'formset': formset,
            'formula': formula,
            'page_title': f'Edit Formula: {formula.name}'
        }
        return render(request, 'production/formula_form.html', context)
    
    def post(self, request, pk):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')

        company = request.user.company
        formula = get_object_or_404(ProductionFormula, pk=pk, company=company)
        
        form = ProductionFormulaForm(request.POST, instance=formula, company=company)
        formset = FormulaIngredientFormSet(
            request.POST,
            instance=formula,
            form_kwargs={'company': company}
        )
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    formula = form.save()
                    formset.save()
                    
                    messages.success(request, f"Production formula '{formula.name}' updated successfully!")
                    return redirect('production:formula_list')
            except Exception as e:
                messages.error(request, f"Error updating formula: {e}")
        else:
            messages.error(request, "Please correct the errors below.")

        context = {
            'form': form,
            'formset': formset, 
            'formula': formula,
            'page_title': f'Edit Formula: {formula.name}'
        }
        return render(request, 'production/formula_form.html', context)

@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.STOCK_KEEPER, User.UserType.VIEWER]), name='dispatch')
class ProductionFormulaDetailView(View):
    def get(self, request, pk):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        formula = get_object_or_404(ProductionFormula, pk=pk, company=company)
        
        ingredients = formula.ingredients.all()
        for ingredient in ingredients:
            ingredient.available = ingredient.material.quantity_on_hand
            ingredient.required_per_unit = ingredient.quantity
            ingredient.status = 'available' if ingredient.available >= ingredient.required_per_unit else 'low'
        
        max_production = float('inf')
        for ingredient in ingredients:
            if ingredient.required_per_unit > 0:
                possible = ingredient.available / ingredient.required_per_unit
                max_production = min(max_production, possible)
        
        if max_production == float('inf'):
            max_production = 0
        
        recent_orders = ProductionOrder.objects.filter(
            formula=formula
        ).order_by('-created_at')[:5]
        
        context = {
            'formula': formula,
            'ingredients': ingredients,
            'max_production': int(max_production),
            'recent_orders': recent_orders,
            'page_title': f'Formula Details: {formula.name}'
        }
        return render(request, 'production/formula_detail.html', context)


# Production Order Views
@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.STOCK_KEEPER]), name='dispatch')
class ProductionOrderListView(View):
    def get(self, request):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        orders = ProductionOrder.objects.filter(company=company)
        
        search_query = request.GET.get('search', '')
        if search_query:
            orders = orders.filter(
                Q(order_number__icontains=search_query) |
                Q(formula__name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
        
        status_filter = request.GET.get('status', '')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        if date_from:
            orders = orders.filter(planned_date__gte=date_from)
        if date_to:
            orders = orders.filter(planned_date__lte=date_to)
        
        paginator = Paginator(orders.order_by('-planned_date', '-created_at'), 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'orders': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
            'date_from': date_from,
            'date_to': date_to,
            'page_title': 'Production Orders'
        }
        return render(request, 'production/order_list.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.STOCK_KEEPER]), name='dispatch')
class ProductionOrderCreateView(View):
    def get(self, request):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        formula_id = request.GET.get('formula_id')
        initial = {}
        if formula_id:
            try:
                formula = ProductionFormula.objects.get(pk=formula_id, company=company)
                initial['formula'] = formula
            except ProductionFormula.DoesNotExist:
                pass
        
        form = ProductionOrderForm(company=company, initial=initial)
        
        context = {
            'form': form,
            'page_title': 'Create Production Order'
        }
        return render(request, 'production/order_form.html', context)
    
    def post(self, request):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        form = ProductionOrderForm(request.POST, company=company)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    order = form.save(commit=False)
                    order.company = company
                    order.created_by = request.user
                    order.save()
                    
                    formula = order.formula
                    for ingredient in formula.ingredients.all():
                        planned_quantity = ingredient.quantity * order.quantity
                        MaterialUsage.objects.create(
                            production_order=order,
                            material=ingredient.material,
                            planned_quantity=planned_quantity
                        )
                    
                    messages.success(request, f"Production order {order.order_number} created successfully!")
                    return redirect('production:order_detail', pk=order.pk)
            except Exception as e:
                messages.error(request, f"Error creating production order: {e}")
        
        context = {
            'form': form,
            'page_title': 'Create Production Order'
        }
        return render(request, 'production/order_form.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.STOCK_KEEPER, User.UserType.VIEWER]), name='dispatch')
class ProductionOrderDetailView(View):
    def get(self, request, pk):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        order = get_object_or_404(ProductionOrder, pk=pk, company=company)
        
        material_usages = order.material_usages.all().select_related('material')
        for usage in material_usages:
            usage.available = usage.material.quantity_on_hand
            usage.status = 'available' if usage.available >= usage.planned_quantity else 'low'
        
        materials_ready = all(usage.status == 'available' for usage in material_usages)
        
        context = {
            'order': order,
            'material_usages': material_usages,
            'materials_ready': materials_ready,
            'page_title': f'Production Order: {order.order_number}'
        }
        return render(request, 'production/order_detail.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER]), name='dispatch')
class ProductionOrderExecuteView(View):
    def get(self, request, pk):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        order = get_object_or_404(ProductionOrder, pk=pk, company=company)
        
        if order.status != ProductionOrder.Status.PLANNED:
            messages.error(request, f"Cannot execute order in '{order.get_status_display()}' status.")
            return redirect('production:order_detail', pk=order.pk)
        
        form = ProductionOrderExecuteForm(instance=order)
        formset = MaterialUsageFormSet(
            instance=order,
            form_kwargs={'company': company}
        )
        
        materials_ready = True
        for usage_form in formset.forms:
            material = usage_form.instance.material
            usage_form.instance.material.enable_batch_tracking = material.enable_batch_tracking
            
            if material.quantity_on_hand < usage_form.instance.planned_quantity:
                materials_ready = False
                messages.warning(
                    request, 
                    f"Insufficient stock of {material.name}. " +
                    f"Required: {usage_form.instance.planned_quantity}, Available: {material.quantity_on_hand}"
                )
        
        context = {
            'order': order,
            'form': form,
            'formset': formset,
            'materials_ready': materials_ready,
            'page_title': f'Execute Production Order: {order.order_number}'
        }
        return render(request, 'production/order_execute.html', context)
    
    def post(self, request, pk):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        order = get_object_or_404(ProductionOrder, pk=pk, company=company)
        
        if order.status != ProductionOrder.Status.PLANNED:
            messages.error(request, f"Cannot execute order in '{order.get_status_display()}' status.")
            return redirect('production:order_detail', pk=order.pk)
        
        form = ProductionOrderExecuteForm(request.POST, instance=order)
        formset = MaterialUsageFormSet(
            request.POST,
            instance=order,
            form_kwargs={'company': company}
        )
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    order = form.save(commit=False)
                    order.status = ProductionOrder.Status.COMPLETED
                    order.start_date = timezone.now()
                    order.completion_date = timezone.now()
                    order.save()
                    
                    for usage_form in formset:
                        usage = usage_form.save(commit=False)
                        
                        if not usage.actual_quantity:
                            usage.actual_quantity = usage.planned_quantity
                        
                        if usage.batch:
                            usage.unit_cost = usage.batch.unit_cost
                        else:
                            usage.unit_cost = usage.material.current_average_cost or Decimal('0.00')
                        
                        usage.usage_date = timezone.now()
                        usage.save()
                        
                        InventoryTransaction.objects.create(
                            company=company,
                            item=usage.material,
                            transaction_type=InventoryTransaction.ADJUSTMENT_OUT,
                            batch=usage.batch,
                            quantity=usage.actual_quantity,
                            unit_cost=usage.unit_cost,
                            transaction_date=timezone.now(),
                            notes=f"Used in Production Order {order.order_number}"
                        )
                        
                        usage.material.quantity_on_hand -= usage.actual_quantity
                        usage.material.save(update_fields=['quantity_on_hand'])
                    
                    order.refresh_from_db()

                    finished_product = order.formula.finished_product
                    produced_quantity = order.quantity * order.formula.unit_quantity
                    
                    total_material_cost = sum(
                        u.actual_quantity * u.unit_cost
                        for u in order.material_usages.all()
                        if u.actual_quantity is not None and u.unit_cost is not None
                    )
                    
                    total_labor_cost = order.actual_labor_cost or (order.formula.labor_cost * order.quantity)
                    total_overhead_cost = order.actual_overhead_cost or (order.formula.overhead_cost * order.quantity)
                    
                    total_cost = total_material_cost + total_labor_cost + total_overhead_cost
                    unit_cost = total_cost / produced_quantity if produced_quantity > 0 else Decimal('0.00')
                    
                    InventoryTransaction.objects.create(
                        company=company,
                        item=finished_product,
                        transaction_type=InventoryTransaction.PURCHASE,
                        quantity=produced_quantity,
                        unit_cost=unit_cost,
                        transaction_date=timezone.now(),
                        notes=f"Produced in Production Order {order.order_number}"
                    )
                    
                    finished_product.quantity_on_hand += produced_quantity
                    finished_product.save(update_fields=['quantity_on_hand'])
                    
                    self.create_journal_entry_for_production(order, total_material_cost, total_labor_cost, total_overhead_cost)
                    
                    messages.success(request, f"Production order {order.order_number} executed successfully!")
                    return redirect('production:order_detail', pk=order.pk)
            except Exception as e:
                messages.error(request, f"Error executing production order: {e}")

        else:
            messages.error(request, "Please correct the errors below.")
        
        materials_ready = True
        for usage_form in formset.forms:
            material = usage_form.instance.material
            usage_form.instance.material.enable_batch_tracking = material.enable_batch_tracking
            
            if material.quantity_on_hand < usage_form.instance.planned_quantity:
                materials_ready = False

        context = {
            'order': order,
            'form': form,
            'formset': formset,
            'materials_ready': materials_ready,
            'page_title': f'Execute Production Order: {order.order_number}'
        }
        return render(request, 'production/order_execute.html', context)
    
    def create_journal_entry_for_production(self, order, material_cost, labor_cost, overhead_cost):
        company = order.company
        finished_product = order.formula.finished_product
        
        try:
            inventory_asset_account = Account.objects.get(
                company=company, 
                system_account=Account.SystemAccount.INVENTORY_ASSET
            )
            cogs_account = Account.objects.get(
                company=company,
                system_account=Account.SystemAccount.COST_OF_GOODS_SOLD
            )
        except Account.DoesNotExist:
            inventory_asset_account = finished_product.asset_account
            cogs_account = finished_product.expense_account
        
        journal_entry = JournalEntry.objects.create(
            company=company,
            date=timezone.now().date(),
            description=f"Production Order {order.order_number}: {finished_product.name}",
            created_by=order.created_by
        )
        
        total_cost = material_cost + labor_cost + overhead_cost
        
        if total_cost > 0:
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=inventory_asset_account,
                description=f"Production of {finished_product.name}",
                debit=total_cost,
                credit=Decimal('0.00')
            )
        
        if material_cost > 0:
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=inventory_asset_account,
                description=f"Raw materials consumed in production",
                debit=Decimal('0.00'),
                credit=material_cost
            )
        
        if labor_cost > 0:
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=cogs_account,
                description=f"Labor cost for production",
                debit=Decimal('0.00'),
                credit=labor_cost
            )
        
        if overhead_cost > 0:
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=cogs_account,
                description=f"Overhead cost for production",
                debit=Decimal('0.00'),
                credit=overhead_cost
            )
        
        return journal_entry

@method_decorator(login_required, name='dispatch')
@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.STOCK_KEEPER]), name='dispatch')
class ProductionOrderCancelView(View):
    def post(self, request, pk):
        if not has_production_access(request.user):
            messages.error(request, "Production management is only available for DELUXE and PREMIUM subscriptions.")
            return redirect('dashboard:home')
        
        company = request.user.company
        order = get_object_or_404(ProductionOrder, pk=pk, company=company)
        
        if order.status != ProductionOrder.Status.PLANNED:
            messages.error(request, f"Cannot cancel order in '{order.get_status_display()}' status.")
            return redirect('production:order_detail', pk=order.pk)
        
        order.status = ProductionOrder.Status.CANCELLED
        order.save(update_fields=['status'])
        
        messages.success(request, f"Production order {order.order_number} has been cancelled.")
        return redirect('production:order_list')


# API Endpoints
@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.STOCK_KEEPER])
def get_formula_details(request, pk):
    if not has_production_access(request.user):
        return JsonResponse({'error': 'Subscription does not include production features'}, status=403)
    
    try:
        company = request.user.company
        formula = ProductionFormula.objects.get(pk=pk, company=company)
        
        ingredients_data = []
        for ingredient in formula.ingredients.all():
            ingredients_data.append({
                'id': ingredient.id,
                'material_id': ingredient.material.id,
                'material_name': ingredient.material.name,
                'quantity_per_unit': float(ingredient.quantity),
                'unit': ingredient.material.unit_of_measurement,
                'available_quantity': float(ingredient.material.quantity_on_hand),
                'notes': ingredient.notes or ''
            })
        
        material_cost = float(formula.material_cost)
        labor_cost = float(formula.labor_cost)
        overhead_cost = float(formula.overhead_cost)
        total_cost = float(formula.total_cost_per_unit)
        
        max_production = float('inf')
        for ingredient in formula.ingredients.all():
            if ingredient.quantity > 0:
                possible = ingredient.material.quantity_on_hand / ingredient.quantity
                max_production = min(max_production, possible)
        
        if max_production == float('inf'):
            max_production = 0
        
        data = {
            'id': formula.id,
            'name': formula.name,
            'finished_product': {
                'id': formula.finished_product.id,
                'name': formula.finished_product.name,
                'unit': formula.finished_product.unit_of_measurement,
                'sale_price': float(formula.finished_product.sale_price)
            },
            'unit_quantity': float(formula.unit_quantity),
            'ingredients': ingredients_data,
            'costs': {
                'material_cost': material_cost,
                'labor_cost': labor_cost,
                'overhead_cost': overhead_cost,
                'total_cost': total_cost
            },
            'max_production': int(max_production),
            'profit_margin': float(formula.profit_margin)
        }
        
        return JsonResponse(data)
    except ProductionFormula.DoesNotExist:
        return JsonResponse({'error': 'Formula not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.STOCK_KEEPER])
def calculate_production_requirements(request):
    if not has_production_access(request.user):
        return JsonResponse({'error': 'Subscription does not include production features'}, status=403)
    
    try:
        formula_id = request.GET.get('formula_id')
        quantity_str = request.GET.get('quantity', '1')
        
        try:
            quantity = Decimal(quantity_str)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid quantity'}, status=400)
        
        company = request.user.company
        formula = ProductionFormula.objects.get(pk=formula_id, company=company)
        
        requirements = []
        all_available = True
        
        for ingredient in formula.ingredients.all():
            required_qty = ingredient.quantity * quantity
            available_qty = ingredient.material.quantity_on_hand
            is_available = available_qty >= required_qty
            
            if not is_available:
                all_available = False
            
            requirements.append({
                'material_id': ingredient.material.id,
                'material_name': ingredient.material.name,
                'required_quantity': float(required_qty),
                'available_quantity': float(available_qty),
                'unit': ingredient.material.unit_of_measurement,
                'is_available': is_available,
                'shortage': float(max(Decimal('0'), required_qty - available_qty)) if not is_available else 0
            })
        
        material_cost = formula.material_cost * quantity
        labor_cost = formula.labor_cost * quantity
        overhead_cost = formula.overhead_cost * quantity
        total_cost = formula.total_cost_per_unit * quantity
        
        output_quantity = formula.unit_quantity * quantity
        
        data = {
            'requirements': requirements,
            'all_available': all_available,
            'costs': {
                'material_cost': float(material_cost),
                'labor_cost': float(labor_cost),
                'overhead_cost': float(overhead_cost),
                'total_cost': float(total_cost)
            },
            'output': {
                'product_name': formula.finished_product.name,
                'quantity': float(output_quantity),
                'unit': formula.finished_product.unit_of_measurement
            }
        }
        
        return JsonResponse(data)
    except ProductionFormula.DoesNotExist:
        return JsonResponse({'error': 'Formula not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)