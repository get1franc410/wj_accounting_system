# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\models.py
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from apps.core.models import Company

class Subscription(models.Model):
    # ... (no changes in this model) ...
    class Plan(models.TextChoices):
        TRIAL = 'TRIAL', '30 Days Free Trial'
        BASIC = 'BASIC', 'Basic (1 User)'
        STANDARD = 'STANDARD', 'Standard (Up to 3 Users)'
        DELUXE = 'DELUXE', 'Deluxe (Up to 5 Users)'
        PREMIUM = 'PREMIUM', 'Premium (Unlimited Users)'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Verification'
        ACTIVE = 'ACTIVE', 'Active'
        EXPIRED = 'EXPIRED', 'Expired'
        CANCELLED = 'CANCELLED', 'Cancelled'

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        default=Plan.TRIAL
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    max_users = models.PositiveIntegerField(default=1)
    activated_on = models.DateTimeField(null=True, blank=True)
    expires_on = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(
        default=False, 
        help_text="Superuser can manually activate or deactivate a subscription."
    )

    PLAN_DETAILS = {
        'TRIAL': {'price_usd': 0, 'duration_days': 30, 'max_users': 3, 'features': ['All features included', 'Up to 3 users', 'Community support']},
        'BASIC': {'price_usd': 45, 'duration_days': 365, 'max_users': 1, 'features': ['Core accounting features', '1 user license', 'Email support']},
        'STANDARD': {'price_usd': 105, 'duration_days': 365, 'max_users': 3, 'features': ['All Basic features', 'Up to 3 users', 'Advanced reporting']},
        'DELUXE': {'price_usd': 375, 'duration_days': 365, 'max_users': 5, 'features': ['All Standard features', 'Up to 5 users', 'Inventory management']},
        'PREMIUM': {'price_usd': 500, 'duration_days': 365, 'max_users': 9999, 'features': ['All Deluxe features', 'Unlimited users', 'Priority support', 'API access']},
    }

    def is_valid(self):
        """Checks if the subscription is currently active and not expired."""
        if not self.is_active or self.status != self.Status.ACTIVE:
            return False
        
        if self.expires_on and timezone.now() > self.expires_on:
            return False
            
        return True

    def get_days_remaining(self):
        """Calculates the number of days until the subscription expires."""
        if not self.expires_on or not self.is_valid():
            return 0
        delta = self.expires_on - timezone.now()
        return max(0, delta.days)

    def extend_subscription(self, years=1):
        """Extends the subscription by a number of years."""
        start_date = self.expires_on if self.expires_on and self.expires_on > timezone.now() else timezone.now()
        self.expires_on = start_date + timedelta(days=365 * years)
        self.status = self.Status.ACTIVE
        self.is_active = True

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        original_plan = None
        if not is_new:
            original_plan = Subscription.objects.get(pk=self.pk).plan
        plan_details = self.PLAN_DETAILS.get(self.plan, {})
        self.max_users = plan_details.get('max_users', 1)
        if is_new:
            if self.activated_on is None:
                self.activated_on = timezone.now()
            duration = plan_details.get('duration_days', 365)
            self.expires_on = self.activated_on + timedelta(days=duration)
        elif self.plan != original_plan and self.plan != self.Plan.TRIAL:
            self.extend_subscription(years=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_plan_display()} for {self.company.name}"


class RegistrationRequest(models.Model):
    """
    Stores registration requests from new users for manual verification.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Verification'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        
    class Industry(models.TextChoices):
        RETAIL = 'RETAIL', 'Retail / E-commerce'
        SERVICES = 'SERVICES', 'Services (Consulting, Agency, etc.)'
        MANUFACTURING = 'MANUFACTURING', 'Manufacturing'
        HOSPITALITY = 'HOSPITALITY', 'Hospitality (Hotel, Restaurant)'
        HEALTHCARE = 'HEALTHCARE', 'Healthcare'
        CONSTRUCTION = 'CONSTRUCTION', 'Construction / Real Estate'
        OTHER = 'OTHER', 'Other'

    # Company & Contact Info
    company_name = models.CharField(max_length=255)
    
    # 🎯 FIX: Added blank=True and default='' to make the field optional
    business_base_country = models.CharField(
        max_length=100, 
        help_text="The primary country where your business operates.",
        blank=True,
        default=''
    )
    
    business_industry = models.CharField(max_length=50, choices=Industry.choices, blank=True, null=True)
    
    contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField(unique=True)
    contact_phone = models.CharField(max_length=30, blank=True)

    # ... (the rest of the model is unchanged) ...
    plan = models.CharField(max_length=20, choices=Subscription.Plan.choices)
    years_paid = models.PositiveSmallIntegerField(default=1, help_text="Set the number of years the client has paid for.")
    payment_receipt = models.FileField(
        upload_to='payment_receipts/%Y/%m/',
        blank=True, 
        null=True,
        help_text="Upload the proof of payment (Required for paid plans)."
    )
    notes = models.TextField(blank=True, help_text="Optional: Any additional information or notes for our team.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, help_text="Notes for the superuser regarding this request.")

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Request from {self.company_name} for {self.get_plan_display()} plan"


class ExchangeRate(models.Model):
    # ... (no changes in this model) ...
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    currency_pair = models.CharField(max_length=10, default="USD_NGN")
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency_pair}: {self.rate} (Valid until {self.valid_until.strftime('%Y-%m-%d')})"

    class Meta:
        ordering = ['-valid_from']
