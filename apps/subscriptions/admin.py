# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Subscription, RegistrationRequest, ExchangeRate
from .signals import approve_registration_request

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('company', 'plan', 'status', 'is_active', 'activated_on', 'expires_on', 'get_days_remaining_display')
    list_filter = ('plan', 'status', 'is_active')
    search_fields = ('company__name',)
    # Make 'plan' and 'expires_on' editable for manual adjustments
    list_editable = ('plan', 'status', 'is_active', 'expires_on')
    readonly_fields = ('activated_on',)
    actions = ['extend_subscription_by_one_year']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')

    @admin.display(description='Days Remaining')
    def get_days_remaining_display(self, obj):
        days = obj.get_days_remaining()
        if days > 0:
            return f"{days} days"
        return "Expired"

    @admin.action(description='Extend selected subscriptions by 1 year')
    def extend_subscription_by_one_year(self, request, queryset):
        """Admin action to extend subscriptions."""
        updated_count = 0
        for subscription in queryset:
            subscription.extend_subscription(years=1)
            subscription.save()
            updated_count += 1
        
        self.message_user(request, f'{updated_count} subscription(s) were successfully extended by one year.')

@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_name', 'plan', 'status', 'years_paid', 'requested_at', 'view_receipt')
    list_filter = ('status', 'plan', 'requested_at')
    search_fields = ('company_name', 'contact_name', 'contact_email')
    readonly_fields = ('requested_at', 'verified_at', 'view_receipt_image')
    list_editable = ('status', 'years_paid')

    fieldsets = (
        ('Request Details', {
            'fields': ('company_name', 'contact_name', 'contact_email', 'contact_phone', 'plan', 'requested_at')
        }),
        ('Verification', {
            # --- ADDED 'years_paid' to the verification section ---
            'fields': ('status', 'years_paid', 'admin_notes', 'view_receipt_image')
        }),
    )

    # ... (rest of the class is unchanged) ...
    def view_receipt(self, obj):
        if obj.payment_receipt:
            return format_html('<a href="{}" target="_blank">View Receipt</a>', obj.payment_receipt.url)
        return "No receipt"
    view_receipt.short_description = "Payment Receipt"

    def view_receipt_image(self, obj):
        if obj.payment_receipt:
            return format_html('<img src="{}" style="max-height: 300px; max-width: 100%;" />', obj.payment_receipt.url)
        return "No receipt uploaded."
    view_receipt_image.short_description = "Receipt Preview"

    def save_model(self, request, obj, form, change):
        """Trigger the approval process when status is changed to APPROVED."""
        original_status = None
        if change:
            try:
                original_status = RegistrationRequest.objects.get(pk=obj.pk).status
            except RegistrationRequest.DoesNotExist:
                pass # Object is new, so no original status
        
        super().save_model(request, obj, form, change)
        
        if obj.status == RegistrationRequest.Status.APPROVED and original_status != RegistrationRequest.Status.APPROVED:
            approve_registration_request(sender=RegistrationRequest, instance=obj, created=False)

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('currency_pair', 'rate', 'valid_from', 'valid_until', 'updated_at')
    readonly_fields = ('updated_at',)
