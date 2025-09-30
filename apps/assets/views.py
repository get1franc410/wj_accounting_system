# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\assets\views.py

from django import forms
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from datetime import datetime, timedelta, date

from apps.reporting.export_utils import export_to_csv, export_to_excel, export_to_pdf
from django.http import JsonResponse

from .models import Asset, AssetMaintenance, DepreciationEntry
from .forms import AssetForm, AssetMaintenanceForm
from apps.authentication.decorators import RoleRequiredMixin
from apps.authentication.models import User
from apps.accounts.models import Account, AccountType
# --- Correctly importing JournalEntry model ---
from apps.journal.models import JournalEntry, JournalEntryLine


class CompanyAssetsMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(company=self.request.user.company)


class AssetListView(LoginRequiredMixin, ListView):
    model = Asset
    template_name = 'assets/asset_list.html'
    context_object_name = 'assets'
    paginate_by = 20

    def get_queryset(self):
        queryset = Asset.objects.filter(
            company=self.request.user.company
        ).select_related('company', 'asset_account').prefetch_related('maintenance_records')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(asset_tag__icontains=search_query)
            )
        
        # Category filter (assuming you have categories)
        category_filter = self.request.GET.get('category')
        if category_filter:
            try:
                category_id = int(category_filter)
                # If you have a category field, uncomment the next line
                # queryset = queryset.filter(category_id=category_id)
                # For now, we'll filter by asset_account as a proxy for category
                queryset = queryset.filter(asset_account_id=category_id)
            except (ValueError, TypeError):
                pass
        
        # Status filter
        status_filter = self.request.GET.get('status')
        if status_filter:
            if status_filter == 'active':
                queryset = queryset.filter(disposal_date__isnull=True)
            elif status_filter == 'disposed':
                queryset = queryset.filter(disposal_date__isnull=False)
            elif status_filter == 'maintenance':
                # Assets that have recent maintenance records
                thirty_days_ago = timezone.now().date() - timedelta(days=30)
                maintenance_asset_ids = AssetMaintenance.objects.filter(
                    asset__company=self.request.user.company,
                    maintenance_date__gte=thirty_days_ago
                ).values_list('asset_id', flat=True)
                queryset = queryset.filter(id__in=maintenance_asset_ids)
        
        # Location filter
        location_filter = self.request.GET.get('location')
        if location_filter:
            # If you have a location field, uncomment the next line
            # queryset = queryset.filter(location__icontains=location_filter)
            # For now, we'll search in description as a proxy
            queryset = queryset.filter(description__icontains=location_filter)
        
        # Date range filters
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(purchase_date__gte=from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(purchase_date__lte=to_date)
            except ValueError:
                pass
        
        # Price range filters
        min_value = self.request.GET.get('min_value')
        max_value = self.request.GET.get('max_value')
        
        if min_value:
            try:
                min_price = Decimal(min_value)
                queryset = queryset.filter(purchase_price__gte=min_price)
            except (ValueError, TypeError):
                pass
        
        if max_value:
            try:
                max_price = Decimal(max_value)
                queryset = queryset.filter(purchase_price__lte=max_price)
            except (ValueError, TypeError):
                pass
        
        # Default ordering
        return queryset.order_by('-purchase_date', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Assets'
        
        # Get filtered queryset for statistics
        filtered_assets = self.get_queryset()
        
        # Calculate summary statistics based on filtered results
        context['total_assets'] = filtered_assets.count()
        
        # Calculate total purchase value
        context['total_purchase_value'] = filtered_assets.aggregate(
            total=Sum('purchase_price')
        )['total'] or Decimal('0.00')
        
        # Calculate total book value (sum of all current book values)
        total_book_value = Decimal('0.00')
        for asset in filtered_assets:
            total_book_value += asset.current_book_value
        context['total_book_value'] = total_book_value
        
        # Calculate total maintenance cost for filtered assets
        asset_ids = filtered_assets.values_list('id', flat=True)
        total_maintenance = AssetMaintenance.objects.filter(
            asset_id__in=asset_ids
        ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
        context['total_maintenance_cost'] = total_maintenance
        
        # Add currency symbol
        context['currency_symbol'] = self.request.user.company.currency_symbol
        
        # Pass filter values back to template for form persistence
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_location'] = self.request.GET.get('location', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['min_value'] = self.request.GET.get('min_value', '')
        context['max_value'] = self.request.GET.get('max_value', '')
        
        # Get categories for dropdown (using asset accounts as categories)
        context['categories'] = Account.objects.filter(
            company=self.request.user.company,
            account_type__name='Fixed Asset'
        ).order_by('name')
        
        return context


# Rest of your views remain the same...
class AssetDetailView(LoginRequiredMixin, RoleRequiredMixin, CompanyAssetsMixin, DetailView):
    model = Asset
    template_name = 'assets/asset_detail.html'
    context_object_name = 'asset'
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['maintenance_form'] = AssetMaintenanceForm()
        context['maintenance_history'] = self.object.maintenance_records.order_by('-maintenance_date')
        return context


class AssetCreateView(LoginRequiredMixin, CreateView):
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_form.html' 
    success_url = reverse_lazy('assets:asset-list') 

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create Asset'
        return context

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        if not form.instance.depreciation_method:
            form.instance.depreciation_method = Asset.DepreciationMethod.STRAIGHT_LINE
        response = super().form_valid(form)
        asset = self.object

        try:
            credit_account = Account.objects.get(
                company=self.request.user.company,
                system_account=Account.SystemAccount.DEFAULT_CASH
            )
            debit_account = asset.asset_account

            if debit_account is None:
                raise ValueError("The asset is not linked to a specific asset account.")

            # Create the main journal entry record, NOW with created_by
            journal = JournalEntry.objects.create(
                company=self.request.user.company,
                date=asset.purchase_date,
                description=f"Acquisition of asset: {asset.name}",
                created_by=self.request.user  # <-- THIS WILL NOW WORK
            )

            # Create the DEBIT line
            JournalEntryLine.objects.create(
                journal_entry=journal,
                account=debit_account,
                debit=asset.purchase_price,
                credit=Decimal('0.00'),
                description=f"Purchase of {asset.name}" # <-- This will also work now
            )

            # Create the CREDIT line
            JournalEntryLine.objects.create(
                journal_entry=journal,
                account=credit_account,
                debit=Decimal('0.00'),
                credit=asset.purchase_price,
                description=f"Payment for {asset.name}" # <-- This will also work now
            )

            messages.success(self.request, "Asset created and acquisition journal entry posted successfully.")

        except Account.DoesNotExist:
            messages.error(self.request, "Critical Error: Could not post journal entry. The default 'CASH' system account is not configured.")
        except ValueError as e:
            messages.error(self.request, f"Error: Could not post journal entry. {e}")
        except Exception as e:
            # This will catch any other unexpected errors, like typos in field names
            messages.error(self.request, f"An unexpected error occurred while posting the journal entry: {e}")

        return response


class AssetUpdateView(LoginRequiredMixin, RoleRequiredMixin, CompanyAssetsMixin, UpdateView):
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_form.html'
    success_url = reverse_lazy('assets:asset-list')
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Asset updated successfully.")
        return super().form_valid(form)


class AssetDeleteView(LoginRequiredMixin, RoleRequiredMixin, CompanyAssetsMixin, DeleteView):
    model = Asset
    template_name = 'assets/asset_confirm_delete.html'
    success_url = reverse_lazy('assets:asset-list')
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT]
    
    def form_valid(self, form):
        messages.success(self.request, "Asset deleted successfully.")
        return super().form_valid(form)


class AddMaintenanceView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = AssetMaintenance
    form_class = AssetMaintenanceForm
    template_name = 'assets/add_maintenance.html'
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        
        # Hide asset field if coming from specific asset page
        if 'asset_pk' in self.kwargs and self.kwargs['asset_pk'] != 0:
            kwargs['hide_asset_field'] = True
        
        return kwargs

    def form_valid(self, form):
        # Handle asset assignment based on URL pattern
        if 'asset_pk' in self.kwargs and self.kwargs['asset_pk'] != 0:
            # Coming from specific asset page - assign the asset
            asset = get_object_or_404(Asset, pk=self.kwargs['asset_pk'], company=self.request.user.company)
            form.instance.asset = asset
        else:
            # Coming from general maintenance form - validate asset selection
            if not form.cleaned_data.get('asset'):
                form.add_error('asset', 'Please select an asset.')
                return self.form_invalid(form)
            
            # Verify the selected asset belongs to the user's company
            selected_asset = form.cleaned_data['asset']
            if selected_asset.company != self.request.user.company:
                form.add_error('asset', 'Invalid asset selection.')
                return self.form_invalid(form)
            
            # Asset is already set by the form, no need to set it again
        
        messages.success(self.request, "Maintenance record added successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        if 'asset_pk' in self.kwargs and self.kwargs['asset_pk'] != 0:
            return reverse_lazy('assets:asset-detail', kwargs={'pk': self.kwargs['asset_pk']})
        return reverse_lazy('assets:maintenance-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'asset_pk' in self.kwargs and self.kwargs['asset_pk'] != 0:
            context['asset'] = get_object_or_404(Asset, pk=self.kwargs['asset_pk'], company=self.request.user.company)
        return context

def export_assets(request):
    """Export assets in requested format with current filters applied"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    # Apply the same filtering logic as the ListView
    queryset = Asset.objects.filter(company=company).select_related('asset_account')
    
    # Apply search filter
    search_query = request.GET.get('search')
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(asset_tag__icontains=search_query)
        )
    
    # Apply category filter
    category_filter = request.GET.get('category')
    if category_filter:
        try:
            category_id = int(category_filter)
            queryset = queryset.filter(asset_account_id=category_id)
        except (ValueError, TypeError):
            pass
    
    # Apply status filter
    status_filter = request.GET.get('status')
    if status_filter:
        if status_filter == 'active':
            queryset = queryset.filter(disposal_date__isnull=True)
        elif status_filter == 'disposed':
            queryset = queryset.filter(disposal_date__isnull=False)
        elif status_filter == 'maintenance':
            thirty_days_ago = timezone.now().date() - timedelta(days=30)
            maintenance_asset_ids = AssetMaintenance.objects.filter(
                asset__company=company,
                maintenance_date__gte=thirty_days_ago
            ).values_list('asset_id', flat=True)
            queryset = queryset.filter(id__in=maintenance_asset_ids)
    
    # Apply date range filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            queryset = queryset.filter(purchase_date__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            queryset = queryset.filter(purchase_date__lte=to_date)
        except ValueError:
            pass
    
    # Apply price range filters
    min_value = request.GET.get('min_value')
    max_value = request.GET.get('max_value')
    
    if min_value:
        try:
            min_price = Decimal(min_value)
            queryset = queryset.filter(purchase_price__gte=min_price)
        except (ValueError, TypeError):
            pass
    
    if max_value:
        try:
            max_price = Decimal(max_value)
            queryset = queryset.filter(purchase_price__lte=max_price)
        except (ValueError, TypeError):
            pass
    
    assets = queryset.order_by('name')
    
    # Headers for export
    headers = [
        'Name', 
        'Description',
        'Purchase Date', 
        'Purchase Price', 
        'Depreciation Method', 
        'Useful Life (Years)', 
        'Salvage Value', 
        'Current Book Value',
        'Accumulated Depreciation',
        'Asset Account',
        'Total Maintenance Cost'
    ]
    
    data = []
    
    for asset in assets:
        data.append([
            asset.name,
            asset.description or '',
            asset.purchase_date.strftime('%Y-%m-%d') if asset.purchase_date else '',
            float(asset.purchase_price) if asset.purchase_price else 0.00,
            asset.get_depreciation_method_display(),
            f"{asset.useful_life_years} years" if asset.useful_life_years else '0 years',
            float(asset.salvage_value) if asset.salvage_value else 0.00,
            float(asset.current_book_value),
            float(asset.get_accumulated_depreciation()),
            asset.asset_account.name if asset.asset_account else 'Not Set',
            float(asset.total_maintenance_cost)
        ])
    
    filename = f"assets_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Asset List"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Assets", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)

def export_maintenance_records(request):
    """Export maintenance records in requested format"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    maintenance_records = AssetMaintenance.objects.filter(
        asset__company=company
    ).select_related('asset').order_by('-maintenance_date')
    
    headers = ['Asset Name', 'Maintenance Date', 'Type', 'Description', 'Cost', 'Next Due Date']
    data = []
    
    for record in maintenance_records:
        data.append([
            record.asset.name,
            record.maintenance_date,
            record.get_maintenance_type_display(),
            record.description,
            record.cost,
            record.next_due_date or 'Not set'
        ])
    
    filename = f"maintenance_records_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Maintenance Records"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Maintenance Records", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)

def export_depreciation_schedule(request):
    """Export depreciation schedule in requested format"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    depreciation_entries = DepreciationEntry.objects.filter(
        asset__company=company
    ).select_related('asset').order_by('asset__name', '-date')
    
    headers = ['Asset Name', 'Date', 'Depreciation Amount', 'Accumulated Depreciation', 'Book Value']
    data = []
    
    for entry in depreciation_entries:
        data.append([
            entry.asset.name,
            entry.date,
            entry.amount,
            entry.asset.accumulated_depreciation,
            entry.asset.current_book_value
        ])
    
    filename = f"depreciation_schedule_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Depreciation Schedule"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Depreciation Schedule", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)
    
class MaintenanceListView(LoginRequiredMixin, ListView):
    model = AssetMaintenance
    template_name = 'assets/maintenance_list.html'
    context_object_name = 'maintenances'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AssetMaintenance.objects.select_related('asset').filter(
            asset__company=self.request.user.company
        ).order_by('-maintenance_date')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(asset__name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(maintenance_type__icontains=search_query)
            )
        
        # Asset filter
        asset_filter = self.request.GET.get('asset')
        if asset_filter:
            queryset = queryset.filter(asset_id=asset_filter)
        
        # Maintenance type filter
        maintenance_type = self.request.GET.get('maintenance_type')
        if maintenance_type:
            queryset = queryset.filter(maintenance_type=maintenance_type)
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(maintenance_date__gte=from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(maintenance_date__lte=to_date)
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter values for form persistence
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_asset'] = self.request.GET.get('asset', '')
        context['selected_maintenance_type'] = self.request.GET.get('maintenance_type', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        # Get assets for filter dropdown
        context['assets'] = Asset.objects.filter(
            company=self.request.user.company
        ).order_by('name')
        
        # Get maintenance type choices from the model
        context['maintenance_type_choices'] = AssetMaintenance.MaintenanceType.choices
        
        # Calculate summary statistics
        all_maintenances = self.get_queryset()
        context['total_maintenances'] = all_maintenances.count()
        context['total_cost'] = all_maintenances.aggregate(
            total=Sum('cost')
        )['total'] or 0
        
        # Recent maintenance stats
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        context['recent_maintenances'] = all_maintenances.filter(
            maintenance_date__gte=thirty_days_ago
        ).count()
        
        # Maintenance type breakdown
        context['repair_count'] = all_maintenances.filter(
            maintenance_type='REPAIR'
        ).count()
        context['routine_count'] = all_maintenances.filter(
            maintenance_type='ROUTINE'
        ).count()
        context['upgrade_count'] = all_maintenances.filter(
            maintenance_type='UPGRADE'
        ).count()
        
        # Currency symbol
        context['currency_symbol'] = self.request.user.company.currency_symbol
        
        return context
