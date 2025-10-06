# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from cryptography.fernet import Fernet
from django.conf import settings
import base64
from django.core.exceptions import ValidationError
from django.utils import timezone
from dateutil.relativedelta import relativedelta

class Company(models.Model):
    """
    Represents the central entity for all data in the system.
    This can be the main user's company or the designated auditor.
    """
    class CompanyType(models.TextChoices):
        USER = 'USER', _('User Company')
        AUDITOR = 'AUDITOR', _('Auditor Company')

    class Currency(models.TextChoices):
        NGN = 'NGN', _('Nigerian Naira (₦)')
        USD = 'USD', _('United States Dollar ($)')
        GBP = 'GBP', _('British Pound (£)')
        CAD = 'CAD', _('Canadian Dollar (C$)')
        
    # Basic Information
    name = models.CharField(max_length=255, unique=True)
    company_type = models.CharField(
        max_length=10,
        choices=CompanyType.choices,
        default=CompanyType.USER
    )
    industry = models.CharField(max_length=100, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_number = models.CharField(max_length=100, blank=True)

    # Contact Information
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    # Configuration
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.NGN,
        blank=False, 
        null=False
    )
    
    # --- MODIFIED: Fiscal Year Fields ---
    fiscal_year_start = models.DateField(
        null=True, blank=True,
        help_text=_("The start date of your financial year. The end date will be set automatically to 12 months later.")
    )
    fiscal_year_end = models.DateField(
        null=True, blank=True, editable=False,
        help_text=_("The calculated end date of your financial year.")
    )
    fiscal_closing_grace_period_months = models.PositiveIntegerField(
        default=3,
        help_text=_("The number of months after the fiscal year ends where accountants can still make entries.")
    )
    
    # Relationships
    primary_contact = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_companies'
    )

    is_licensed = models.BooleanField(default=False)
    # Status & Timestamps
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_company_type_display()})"

    def save(self, *args, **kwargs):
        # --- NEW: Automatically calculate fiscal_year_end ---
        if self.fiscal_year_start:
            # The end date is 12 months after the start, minus one day.
            self.fiscal_year_end = self.fiscal_year_start + relativedelta(months=12) - relativedelta(days=1)
        
        self.full_clean()
        super().save(*args, **kwargs)

    # --- NEW: Helper properties for date checks ---
    @property
    def hard_closing_date(self):
        """
        Calculates the date before which no non-admin user can post transactions.
        This is the end of the previous fiscal year plus the grace period.
        """
        if not self.fiscal_year_start:
            return None
        
        today = timezone.now().date()
        # Find the start of the current fiscal year relative to today
        current_fiscal_year_start = self.fiscal_year_start
        while current_fiscal_year_start + relativedelta(months=12) <= today:
            current_fiscal_year_start += relativedelta(months=12)
            
        # The "hard close" applies to the period *before* the previous fiscal year ended
        previous_fiscal_year_end = current_fiscal_year_start - relativedelta(days=1)
        
        # The hard closing date is the end of that previous year + grace period
        hard_close_date = previous_fiscal_year_end + relativedelta(months=self.fiscal_closing_grace_period_months)
        return hard_close_date

    def is_period_closed_for_user(self, transaction_date, user):
        """
        Check if a given date falls into a period that is closed for the user's role.
        Returns True if closed, False otherwise.
        """
        hard_close_date = self.hard_closing_date
        if not hard_close_date:
            return False # No fiscal year is set, so nothing is closed

        # If the transaction date is before the hard closing date
        if transaction_date <= hard_close_date:
            # Only Admins can post to a hard-closed period
            if user.user_type != 'ADMIN':
                return True
        
        return False

    @classmethod
    def get_user_company(cls):
        return cls.objects.filter(company_type=cls.CompanyType.USER).first()

    @classmethod
    def get_auditor_company(cls):
        return cls.objects.filter(company_type=cls.CompanyType.AUDITOR).first()
    
    @property
    def currency_symbol(self):
        """Get the currency symbol for this company"""
        from .utils import get_currency_symbol
        return get_currency_symbol(self.currency)
    
    @property
    def currency_icon_class(self):
        """Get the currency icon class for this company"""
        from .utils import get_currency_icon_class
        return get_currency_icon_class(self.currency)
    
class EmailConfiguration(models.Model):
    """Stores email configuration for backup sending"""
    company = models.OneToOneField(
        Company, 
        on_delete=models.CASCADE,
        related_name='email_config'
    )
    email_address = models.EmailField(help_text="Gmail address for sending backups")
    app_password = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Gmail App Password (not your regular password)"
    )
    smtp_server = models.CharField(max_length=100, default='smtp.gmail.com')
    smtp_port = models.IntegerField(default=587)
    use_tls = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Email Config for {self.company.name}"

    class Meta:
        verbose_name = "Email Configuration"
        verbose_name_plural = "Email Configurations"