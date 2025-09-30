# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\backup\models.py
import os
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from apps.core.models import Company
from django.core.files.storage import default_storage

# Helper function to define the upload path for backup files
def backup_file_path(instance, filename):
    # Files will be uploaded to MEDIA_ROOT/backups/<company_name>/<filename>
    return f'backups/{instance.company.name}/{filename}'

class Backup(models.Model):
    """Represents a single, completed backup instance."""
    class StatusChoices(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='backups'
    )
    # The actual backup file (e.g., a .zip or .csv)
    file = models.FileField(upload_to=backup_file_path, null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.IN_PROGRESS)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Notes on the backup, e.g., reason for failure.")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Backup for {self.company.name} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class BackupSettings(models.Model):
    """Stores the configuration for backups and reminders for the User Company."""
    
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='backup_settings',
        limit_choices_to={'company_type': Company.CompanyType.USER}
    )
    
    # Backup Schedule Settings
    backup_enabled = models.BooleanField(default=True, help_text="Enable automatic backups")
    backup_frequency_days = models.PositiveIntegerField(
        default=7, 
        help_text="How often to backup (in days). E.g., 1=daily, 7=weekly, 30=monthly"
    )
    backup_time = models.TimeField(
        default='02:00:00',
        help_text="What time of day to run backups (24-hour format)"
    )
    last_backup_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When the last backup was completed"
    )
    
    # Date Range Controls for Backups
    backup_date_range_enabled = models.BooleanField(
        default=False, 
        help_text="Enable date range filtering for backups"
    )
    backup_start_date = models.DateField(
        null=True, blank=True,
        help_text="Start date for backup data (leave blank for all data)"
    )
    backup_end_date = models.DateField(
        null=True, blank=True,
        help_text="End date for backup data (leave blank for current date)"
    )
    
    # Incremental Backup Settings
    incremental_backup_enabled = models.BooleanField(
        default=False,
        help_text="Only backup data changed since last successful backup"
    )
    
    # Audit Document Controls
    audit_date_range_enabled = models.BooleanField(
        default=False,
        help_text="Enable date range filtering for audit documents"
    )
    audit_start_date = models.DateField(
        null=True, blank=True,
        help_text="Start date for audit period (e.g., 6 months ago)"
    )
    audit_end_date = models.DateField(
        null=True, blank=True,
        help_text="End date for audit period (leave blank for current date)"
    )

    # Audit Reminder Settings
    audit_reminders_enabled = models.BooleanField(default=True, help_text="Enable audit reminders")
    audit_frequency_days = models.PositiveIntegerField(
        default=30,
        help_text="How often to send audit reminders (in days). E.g., 30=monthly, 90=quarterly"
    )
    audit_reminder_day_of_month = models.PositiveIntegerField(
        default=1,
        help_text="Which day of the month to send reminders (1-28)"
    )
    last_audit_reminder_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the last audit reminder was sent"
    )
    
    # Smart Debtor Reminder Settings
    debtor_reminders_enabled = models.BooleanField(default=True, help_text="Enable automatic debtor reminders")
    
    # Pre-due date reminders
    send_before_due_enabled = models.BooleanField(
        default=True, 
        help_text="Send reminders before due date"
    )
    days_before_due_date = models.PositiveIntegerField(
        default=3,
        help_text="Days before due date to send first reminder"
    )
    
    # Post-due date reminders
    send_after_due_enabled = models.BooleanField(
        default=True, 
        help_text="Send reminders after due date"
    )
    days_after_due_first = models.PositiveIntegerField(
        default=1,
        help_text="Days after due date to send first overdue reminder"
    )
    days_after_due_second = models.PositiveIntegerField(
        default=7,
        help_text="Days after due date to send second overdue reminder"
    )
    days_after_due_final = models.PositiveIntegerField(
        default=30,
        help_text="Days after due date to send final overdue reminder"
    )
    
    # Reminder timing
    reminder_time = models.TimeField(
        default='09:00:00',
        help_text="What time of day to send reminders (24-hour format)"
    )
    
    # Frequency control
    reminder_check_frequency_days = models.PositiveIntegerField(
        default=1,
        help_text="How often to check for due reminders (1=daily, 7=weekly)"
    )
    
    last_debtor_reminder_check = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When debtor reminders were last checked"
    )

    def __str__(self):
        return f"Settings for {self.company.name}"
    
    def is_backup_due(self):
        """Check if a backup is due based on frequency settings"""
        if not self.backup_enabled:
            return False
        
        if not self.last_backup_date:
            return True
        
        from django.utils import timezone
        days_since_backup = (timezone.now() - self.last_backup_date).days
        return days_since_backup >= self.backup_frequency_days
    
    def is_audit_reminder_due(self):
        """Check if an audit reminder is due"""
        if not self.audit_reminders_enabled:
            return False
        
        from django.utils import timezone
        now = timezone.now()
        
        if not self.last_audit_reminder_date:
            return True
        
        days_since_reminder = (now - self.last_audit_reminder_date).days
        return days_since_reminder >= self.audit_frequency_days
    
    def is_debtor_reminder_check_due(self):
        """Check if it's time to check for debtor reminders"""
        if not self.debtor_reminders_enabled:
            return False
        
        if not self.last_debtor_reminder_check:
            return True
        
        from django.utils import timezone
        days_since_check = (timezone.now() - self.last_debtor_reminder_check).days
        return days_since_check >= self.reminder_check_frequency_days

class BackupRecipient(models.Model):
    """Represents a single email address that will receive backup files."""
    settings = models.ForeignKey(
        BackupSettings,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    email = models.EmailField()

    class Meta:
        unique_together = ('settings', 'email')
        verbose_name = "Backup Recipient"
        verbose_name_plural = "Backup Recipients"

    def __str__(self):
        return self.email

class DebtorReminderLog(models.Model):
    """Track when reminders are sent to avoid duplicates"""
    class ReminderType(models.TextChoices):
        BEFORE_DUE = 'BEFORE_DUE', 'Before Due Date'
        FIRST_OVERDUE = 'FIRST_OVERDUE', 'First Overdue'
        SECOND_OVERDUE = 'SECOND_OVERDUE', 'Second Overdue'
        FINAL_OVERDUE = 'FINAL_OVERDUE', 'Final Overdue'
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    transaction = models.ForeignKey('transactions.Transaction', on_delete=models.CASCADE)
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE)
    reminder_type = models.CharField(max_length=20, choices=ReminderType.choices)
    sent_date = models.DateTimeField(auto_now_add=True)
    email_sent_to = models.EmailField()
    
    class Meta:
        unique_together = ('transaction', 'reminder_type')
        ordering = ['-sent_date']
    
    def __str__(self):
        return f"{self.reminder_type} reminder for {self.transaction} sent to {self.customer.name}"
