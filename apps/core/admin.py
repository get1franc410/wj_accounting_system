# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\admin.py

from django.contrib import admin
from .models import Company, EmailConfiguration

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Company model.
    """
    list_display = ('name', 'company_type', 'email', 'phone', 'is_active')
    list_filter = ('company_type', 'is_active', 'industry')
    search_fields = ('name', 'email', 'registration_number', 'tax_number')
    
    fieldsets = (
        (None, {
            'fields': ('company_type', 'name', 'logo')
        }),
        ('Legal Information', {
            'fields': ('industry', 'registration_number', 'tax_number')
        }),
        ('Contact Information', {
            'fields': ('address', 'phone', 'email', 'website')
        }),
        ('System Configuration', {
            'fields': ('currency', 'fiscal_year_start', 'primary_contact')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ('company', 'email_address', 'is_active')
    list_filter = ('is_active',)
