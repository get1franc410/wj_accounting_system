# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from cryptography.fernet import Fernet
from django.conf import settings
import base64
from django.core.exceptions import ValidationError

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
    
    fiscal_year_start = models.DateField(null=True, blank=True)
    
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
        # --- FIX: Removed the overly restrictive UniqueConstraint ---
        # The 'name' field is already unique=True, which is correct.
        # We do not need a constraint on company_type.
        # constraints = [
        #     models.UniqueConstraint(fields=['company_type'], name='unique_company_type')
        # ]

    def __str__(self):
        return f"{self.name} ({self.get_company_type_display()})"

    def save(self, *args, **kwargs):
        # The full_clean() call is good, but it was what triggered the error.
        # Now that the constraint is gone, it will work correctly.
        self.full_clean()
        super().save(*args, **kwargs)

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