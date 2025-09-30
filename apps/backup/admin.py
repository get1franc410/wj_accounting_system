# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\backup\admin.py

from django.contrib import admin
from .models import Backup, BackupSettings, BackupRecipient, DebtorReminderLog

class BackupRecipientInline(admin.TabularInline):
    """
    Allows you to edit recipient emails directly within the BackupSettings admin page.
    """
    model = BackupRecipient
    extra = 1  # Show one extra blank line for a new email

@admin.register(BackupSettings)
class BackupSettingsAdmin(admin.ModelAdmin):
    """
    Admin view for BackupSettings. It includes the recipient emails.
    """
    list_display = (
        'company', 
        'backup_enabled', 
        'backup_frequency_display',
        'audit_reminders_enabled',
        'audit_frequency_display',
        'debtor_reminders_enabled'
    )
    list_filter = ('backup_enabled', 'audit_reminders_enabled', 'debtor_reminders_enabled')
    search_fields = ('company__name',)
    inlines = [BackupRecipientInline]
    
    fieldsets = (
        ('Company', {
            'fields': ('company',)
        }),
        ('Backup Settings', {
            'fields': (
                'backup_enabled',
                'backup_frequency_days',
                'backup_time',
                'last_backup_date'
            )
        }),
        ('Audit Reminder Settings', {
            'fields': (
                'audit_reminders_enabled',
                'audit_frequency_days',
                'audit_reminder_day_of_month',
                'last_audit_reminder_date'
            )
        }),
        ('Debtor Reminder Settings', {
            'fields': (
                'debtor_reminders_enabled',
                'send_before_due_enabled',
                'days_before_due_date',
                'send_after_due_enabled',
                'days_after_due_first',
                'days_after_due_second',
                'days_after_due_final',
                'reminder_time',
                'reminder_check_frequency_days',
                'last_debtor_reminder_check'
            )
        }),
    )
    
    readonly_fields = ('last_backup_date', 'last_audit_reminder_date', 'last_debtor_reminder_check')
    
    def backup_frequency_display(self, obj):
        """Display backup frequency in a readable format"""
        if obj.backup_frequency_days == 1:
            return "Daily"
        elif obj.backup_frequency_days == 7:
            return "Weekly"
        elif obj.backup_frequency_days == 30:
            return "Monthly"
        else:
            return f"Every {obj.backup_frequency_days} days"
    backup_frequency_display.short_description = "Backup Frequency"
    
    def audit_frequency_display(self, obj):
        """Display audit frequency in a readable format"""
        if obj.audit_frequency_days == 30:
            return "Monthly"
        elif obj.audit_frequency_days == 90:
            return "Quarterly"
        elif obj.audit_frequency_days == 365:
            return "Yearly"
        else:
            return f"Every {obj.audit_frequency_days} days"
    audit_frequency_display.short_description = "Audit Frequency"

@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    """
    Admin view for the Backup history. This is crucial for monitoring.
    """
    list_display = ('company', 'status', 'created_at', 'file_size', 'has_file')
    list_filter = ('status', 'company', 'created_at')
    search_fields = ('company__name', 'notes')
    readonly_fields = ('created_at', 'file_size')
    date_hierarchy = 'created_at'
    
    def has_file(self, obj):
        """Check if backup has a file"""
        return bool(obj.file)
    has_file.boolean = True
    has_file.short_description = "Has File"
    
    def file_size(self, obj):
        """Display file size if file exists"""
        if obj.file:
            try:
                size = obj.file.size
                if size < 1024:
                    return f"{size} bytes"
                elif size < 1024 * 1024:
                    return f"{size / 1024:.1f} KB"
                else:
                    return f"{size / (1024 * 1024):.1f} MB"
            except:
                return "Unknown"
        return "No file"
    file_size.short_description = "File Size"

@admin.register(DebtorReminderLog)
class DebtorReminderLogAdmin(admin.ModelAdmin):
    """
    Admin view for debtor reminder logs
    """
    list_display = (
        'company', 
        'customer', 
        'transaction_reference',
        'reminder_type', 
        'sent_date', 
        'email_sent_to'
    )
    list_filter = ('reminder_type', 'company', 'sent_date')
    search_fields = ('customer__name', 'email_sent_to', 'transaction__reference_number')
    readonly_fields = ('sent_date',)
    date_hierarchy = 'sent_date'
    
    def transaction_reference(self, obj):
        """Display transaction reference number"""
        return obj.transaction.reference_number if obj.transaction else "N/A"
    transaction_reference.short_description = "Transaction Ref"
    
    # Prevent adding/editing logs through admin (they should be created by the system)
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
