# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\customers\admin.py

from django.contrib import admin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Admin interface for the Customer model.
    """
    list_display = (
        'name',
        'company',
        'entity_type',
        'email',
        'phone',
        'receivable_balance', # Shows the calculated property
        'payable_balance',  # Shows the calculated property
    )
    list_filter = ('company', 'entity_type')
    search_fields = ('name', 'email', 'company__name')
    ordering = ('company', 'name',)

    # Use raw_id_fields for foreign keys to improve performance
    raw_id_fields = ('company', 'receivable_account', 'payable_account')

    # Define fields to be displayed in the detail/edit view
    fieldsets = (
        (None, {
            'fields': ('company', 'name', 'entity_type')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address')
        }),
        ('Accounting Details', {
            'fields': ('receivable_account', 'payable_account', 'credit_limit')
        }),
    )

    # Make linked accounts read-only in the admin to prevent accidental changes
    # These should only be managed by the views.
    readonly_fields = ('receivable_account', 'payable_account')

