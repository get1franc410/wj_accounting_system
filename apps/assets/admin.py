# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\assets\admin.py

from django.contrib import admin
from .models import Asset, AssetMaintenance, DepreciationEntry

class AssetMaintenanceInline(admin.TabularInline):
    """
    Allows viewing and adding maintenance records directly from the Asset admin page.
    """
    model = AssetMaintenance
    extra = 0  # Don't show extra blank forms by default
    readonly_fields = ('maintenance_date', 'maintenance_type', 'description', 'cost') # Make them read-only in this compact view
    can_delete = False # Usually, you'd want to manage these separately

    def has_add_permission(self, request, obj=None):
        return False # Prevent adding from here to encourage using the main form

class DepreciationEntryInline(admin.TabularInline):
    """
    Shows the history of depreciation postings for this asset.
    This should be read-only as it's an audit log created by the system.
    """
    model = DepreciationEntry
    extra = 0
    readonly_fields = ('date', 'amount', 'journal_entry')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False # These are system-generated, never manually added

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    """
    Admin interface for the main Asset model.
    """
    list_display = ('name', 'company', 'purchase_date', 'purchase_price', 'current_book_value')
    list_filter = ('company', 'depreciation_method', 'purchase_date')
    search_fields = ('name', 'description', 'company__name')
    readonly_fields = ('current_book_value', 'get_accumulated_depreciation')
    
    # Display related maintenance and depreciation history on the asset's page
    inlines = [AssetMaintenanceInline, DepreciationEntryInline]

    fieldsets = (
        ('Asset Information', {
            'fields': ('company', 'name', 'description')
        }),
        ('Financials', {
            'fields': ('purchase_date', 'purchase_price', 'salvage_value', 'current_book_value', 'get_accumulated_depreciation')
        }),
        ('Depreciation Settings', {
            'fields': ('depreciation_method', 'useful_life_years')
        }),
        ('Linked Accounts', {
            'fields': ('asset_account', 'accumulated_depreciation_account', 'depreciation_expense_account')
        }),
    )

@admin.register(AssetMaintenance)
class AssetMaintenanceAdmin(admin.ModelAdmin):
    """
    Admin interface for managing asset maintenance records.
    """
    list_display = ('asset', 'maintenance_date', 'maintenance_type', 'cost')
    list_filter = ('maintenance_date', 'maintenance_type', 'asset__company')
    search_fields = ('asset__name', 'description')

@admin.register(DepreciationEntry)
class DepreciationEntryAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing the audit trail of depreciation postings.
    This view is primarily for inspection and should be read-only.
    """
    list_display = ('asset', 'date', 'amount', 'journal_entry')
    list_filter = ('date', 'asset__company')
    search_fields = ('asset__name',)
    # Make all fields read-only to protect the audit trail
    readonly_fields = ('asset', 'journal_entry', 'date', 'amount', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
