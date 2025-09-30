# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\inventory\admin.py

from django.contrib import admin
from .models import InventoryItem, InventoryTransaction

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    """
    Admin interface for InventoryItem model.
    """
    list_display = (
        'name', 'sku', 'company', 'item_type', 'quantity_on_hand', 
        'sale_price', 'purchase_price', 'is_low_on_stock'
    )
    list_filter = ('company', 'item_type')
    search_fields = ('name', 'sku', 'company__name')
    ordering = ('company', 'name',)
    
    # Make foreign key fields easier to manage
    raw_id_fields = ('income_account', 'expense_account', 'asset_account')

    # Add a fieldset to organize the form
    fieldsets = (
        (None, {
            'fields': ('company', 'name', 'sku', 'item_type', 'description')
        }),
        ('Pricing & Stock', {
            'fields': ('unit_of_measurement', 'purchase_price', 'sale_price', 'quantity_on_hand', 'reorder_level')
        }),
        ('Accounting Integration', {
            'classes': ('collapse',), # Make this section collapsible
            'fields': ('income_account', 'expense_account', 'asset_account')
        }),
    )
    
    # quantity_on_hand should not be editable here
    readonly_fields = ('quantity_on_hand',)

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    """
    Admin interface for InventoryTransaction model.
    """
    list_display = ('item', 'transaction_type', 'quantity', 'transaction_date', 'company')
    list_filter = ('company', 'transaction_type', 'transaction_date')
    search_fields = ('item__name', 'company__name')
    ordering = ('-transaction_date',)
    
    # Use raw_id_fields for better performance with large numbers of items
    raw_id_fields = ('item',)
