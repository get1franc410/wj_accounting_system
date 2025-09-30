# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\accounts\admin.py

from django.contrib import admin
from .models import Account, AccountType

@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):
    """
    Admin interface for AccountType model.
    """
    # FIX: Add 'category' to the display and make it a filter
    list_display = ('name', 'category')
    search_fields = ('name',)
    list_filter = ('category',)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """
    Admin interface for the main Account model.
    """
    list_display = (
        'account_number', 
        'name', 
        'account_type', 
        'company', 
        'parent', 
        'is_control_account', 
        'is_active'
    )
    list_filter = ('company', 'account_type', 'is_active', 'is_control_account')
    search_fields = ('name', 'account_number', 'company__name')
    ordering = ('company', 'account_number',)
    raw_id_fields = ('parent',)
