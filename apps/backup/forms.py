# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\backup\forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import BackupSettings, BackupRecipient
from apps.core.models import Company, EmailConfiguration

class BackupSettingsForm(forms.ModelForm):
    """Form for backup and reminder settings."""
    
    class Meta:
        model = BackupSettings
        fields = [
            'backup_enabled', 'backup_frequency_days', 'backup_time',
            'backup_date_range_enabled', 'backup_start_date', 'backup_end_date',
            'incremental_backup_enabled',
            'audit_reminders_enabled', 'audit_frequency_days', 'audit_reminder_day_of_month',
            'audit_date_range_enabled', 'audit_start_date', 'audit_end_date',
            'debtor_reminders_enabled', 'send_before_due_enabled', 'days_before_due_date',
            'send_after_due_enabled', 'days_after_due_first', 'days_after_due_second', 
            'days_after_due_final', 'reminder_time', 'reminder_check_frequency_days'
        ]
        widgets = {
            'backup_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'reminder_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'backup_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'backup_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'audit_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'audit_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'backup_frequency_days': forms.NumberInput(attrs={'min': '1', 'max': '365', 'class': 'form-control'}),
            'audit_frequency_days': forms.NumberInput(attrs={'min': '1', 'max': '365', 'class': 'form-control'}),
            'audit_reminder_day_of_month': forms.NumberInput(attrs={'min': '1', 'max': '28', 'class': 'form-control'}),
            'days_before_due_date': forms.NumberInput(attrs={'min': '1', 'max': '30', 'class': 'form-control'}),
            'days_after_due_first': forms.NumberInput(attrs={'min': '1', 'max': '30', 'class': 'form-control'}),
            'days_after_due_second': forms.NumberInput(attrs={'min': '1', 'max': '90', 'class': 'form-control'}),
            'days_after_due_final': forms.NumberInput(attrs={'min': '1', 'max': '365', 'class': 'form-control'}),
            'reminder_check_frequency_days': forms.NumberInput(attrs={'min': '1', 'max': '7', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text and labels
        self.fields['backup_frequency_days'].help_text = "1 = Daily, 7 = Weekly, 30 = Monthly, etc."
        self.fields['audit_frequency_days'].help_text = "30 = Monthly, 90 = Quarterly, 365 = Yearly"
        self.fields['backup_date_range_enabled'].help_text = "Only backup data within specified date range"
        self.fields['incremental_backup_enabled'].help_text = "Only backup data changed since last backup (faster)"
        self.fields['audit_date_range_enabled'].help_text = "Only include data within audit period (e.g., last 6 months)"
        self.fields['days_before_due_date'].help_text = "Send courtesy reminder X days before due date"
        self.fields['days_after_due_first'].help_text = "Send first overdue notice X days after due date"
        self.fields['days_after_due_second'].help_text = "Send second overdue notice X days after due date"
        self.fields['days_after_due_final'].help_text = "Send final overdue notice X days after due date"
        self.fields['reminder_check_frequency_days'].help_text = "1 = Check daily, 7 = Check weekly"

class BackupRecipientForm(forms.ModelForm):
    """Form for a single backup recipient email."""
    class Meta:
        model = BackupRecipient
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'Enter recipient email'})
        }

RecipientFormSet = inlineformset_factory(
    BackupSettings,
    BackupRecipient,
    fields=['email'],
    extra=1,
    can_delete=True,
    widgets={
        'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'})
    }
)
