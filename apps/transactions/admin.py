# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\transactions\admin.py

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.db.models import F
from .models import Transaction, TransactionItem, TransactionCategory

class PaymentStatusFilter(SimpleListFilter):
    """Custom filter for payment status based on calculated values"""
    title = 'Payment Status'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return (
            ('paid', 'Paid'),
            ('unpaid', 'Unpaid'),
            ('partial', 'Partially Paid'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'paid':
            # Paid: amount_paid >= total_amount
            return queryset.filter(amount_paid__gte=F('total_amount'))
        elif self.value() == 'unpaid':
            # Unpaid: amount_paid = 0
            return queryset.filter(amount_paid=0)
        elif self.value() == 'partial':
            # Partially paid: 0 < amount_paid < total_amount
            return queryset.filter(amount_paid__gt=0, amount_paid__lt=F('total_amount'))
        return queryset

@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'default_account', 'company', 'is_active')
    list_filter = ('company', 'account_type', 'is_active')
    search_fields = ('name', 'default_account__name', 'account_type__name')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'name', 'description', 'is_active')
        }),
        ('Account Configuration', {
            'fields': ('account_type', 'default_account', 'allowed_transaction_types'),
            'description': 'Configure which account type and transaction types this category supports'
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company', 'account_type', 'default_account')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter accounts by company when editing"""
        if db_field.name == "default_account":
            if hasattr(request, '_obj_'):
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    company=request._obj_.company
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_form(self, request, obj=None, **kwargs):
        # Store the object in request for use in formfield_for_foreignkey
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

class TransactionItemInline(admin.TabularInline):
    """Allows editing of TransactionItems directly within the Transaction admin page."""
    model = TransactionItem
    extra = 0
    readonly_fields = ('line_total',)
    raw_id_fields = ('item',) 

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Enhanced admin interface for the Transaction model with payment status filtering."""
    inlines = [TransactionItemInline]
    
    list_display = (
        'id',
        'date',
        'transaction_type',
        'category',
        'customer',
        'total_amount',
        'colored_payment_status',  # 🎯 CUSTOM METHOD WITH COLORS
        'created_by',
        'company',
        'journal_entry'
    )
    
    # 🎯 PERFECT: Custom payment status filter that works with database queries
    list_filter = ('transaction_type', 'company', 'date', PaymentStatusFilter)
    search_fields = ('id', 'customer__name', 'reference_number', 'description')
    ordering = ('-date', '-created_at')
    
    fieldsets = (
        ('Core Information', {
            'fields': ('company', 'transaction_type', 'customer', 'date', 'due_date', 'reference_number')
        }),
        ('Categorization', {
            'fields': ('category', 'description'),
        }),
        ('Financials', {
            'fields': ('total_amount', 'amount_paid', 'balance_due')
        }),
        ('Links & Attachments', {
            'fields': ('journal_entry', 'attachment')
        }),
        ('Audit Trail', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = (
        'total_amount', 
        'balance_due', 
        'journal_entry',
        'created_at',
        'updated_at',
        'created_by'
    )

    raw_id_fields = ('customer',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'company', 'customer', 'journal_entry', 'category', 'created_by'
        ).prefetch_related('items')
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new transaction"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def colored_payment_status(self, obj):
        """Display payment status with professional color coding"""
        status = obj.payment_status
        color_mapping = {
            'Paid': '#28a745',           # Success green
            'Partially Paid': '#ffc107', # Warning yellow
            'Unpaid': '#dc3545',         # Danger red
            'N/A': '#6c757d'             # Muted gray
        }
        color = color_mapping.get(status, '#000000')
        
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 2px 6px; '
            'border-radius: 3px; background-color: {}20;">{}</span>',
            color, color, status
        )
    
    colored_payment_status.short_description = 'Payment Status'
    colored_payment_status.admin_order_field = 'amount_paid'  # Allow sorting

    def get_list_display_links(self, request, list_display):
        """Make transaction ID and date clickable"""
        return ('id', 'date')
    
    def has_delete_permission(self, request, obj=None):
        """Restrict deletion to maintain audit trail"""
        # Only superusers can delete transactions
        return request.user.is_superuser
    
    class Media:
        css = {
            'all': ('admin/css/custom_transaction_admin.css',)
        }
