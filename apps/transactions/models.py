# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\transactions\models.py

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.authentication.models import User 
from apps.core.models import Company
from apps.customers.models import Customer
from apps.inventory.models import InventoryItem
from apps.journal.models import JournalEntry
from apps.accounts.models import AccountType
from .constants import TransactionType

class TransactionCategory(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    
    # 🎯 DYNAMIC LINK TO CHART OF ACCOUNTS
    account_type = models.ForeignKey(
        AccountType,
        on_delete=models.PROTECT,
        help_text="Select the account type this category belongs to"
    )
    
    # 🎯 CENTRALIZED TRANSACTION TYPES
    allowed_transaction_types = models.JSONField(
        default=list,
        help_text="Transaction types that can use this category"
    )
    
    # Optional default account from the selected account type
    default_account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.PROTECT,
        null=True, blank=True,
        help_text="Default account for this category (must belong to selected account type)"
    )
    
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['company', 'name']
        ordering = ['account_type__category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.account_type.get_category_display()})"
    
    def get_compatible_transaction_types(self):
        """Return human-readable transaction types using centralized mapping"""
        return [
            TransactionType.get_display_name(t) 
            for t in self.allowed_transaction_types
        ]
    
    def is_compatible_with_transaction_type(self, transaction_type):
        """Check if category supports the transaction type"""
        return transaction_type in self.allowed_transaction_types

    def get_suggested_accounts(self):
        """Get all accounts that belong to this category's account type"""
        from apps.accounts.models import Account
        
        if self.default_account:
            return [self.default_account]
            
        # Return all accounts of the same type
        return Account.objects.filter(
            company=self.company,
            account_type=self.account_type
        ).order_by('account_number')
    
    def clean(self):
        """Validate that default_account belongs to the selected account_type"""
        super().clean()
        if self.default_account and self.account_type:
            if self.default_account.account_type != self.account_type:
                raise ValidationError({
                    'default_account': f'Selected account must belong to account type: {self.account_type.name}'
                })

class Transaction(models.Model):
    """
    The central model for all financial events like sales, purchases, and expenses.
    Saving a Transaction automatically generates the corresponding Journal Entry.
    """
    
    # 🎯 USE CENTRALIZED TRANSACTION TYPES
    TRANSACTION_TYPE_CHOICES = TransactionType.CHOICES

    # Core Fields
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='transactions',
        null=True, blank=True,
        help_text="The customer or vendor for this transaction."
    )
    description = models.TextField(blank=True, help_text="Internal notes or memo.")
    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transactions',
        help_text="Categorize this transaction for reporting (e.g., Fuel, Utilities)."
    )

    # Financials
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), editable=False)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    # Linked Documents
    journal_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transaction',
        editable=False
    )
    attachment = models.FileField(upload_to='transaction_attachments/', null=True, blank=True)
    reference_number = models.CharField(max_length=100, blank=True, help_text="e.g., Invoice #, Bill #, Receipt #")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_transactions',
        editable=False
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='updated_transactions',
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} #{self.id} for {self.customer or 'N/A'}"

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    @property
    def payment_status(self):
        if self.total_amount == Decimal('0.00'):
            return "N/A"
        if self.balance_due <= 0:
            return "Paid"
        if self.balance_due < self.total_amount:
            return "Partially Paid"
        return "Unpaid"
    
    @property
    def subtotal(self):
        """Calculate subtotal (before tax)"""
        if self.items.exists():
            return sum(item.line_total for item in self.items.all())
        return self.total_amount
    
    @property
    def tax_amount(self):
        """Calculate tax amount"""
        # For now, return 0 - you can implement tax calculation later
        return Decimal('0.00')
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Auto-update customer balances when transaction changes
        if self.customer:
            self.customer.update_balances()

class TransactionItem(models.Model):
    """
    Represents a single line item within a Transaction (e.g., a product on an invoice).
    """
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='transaction_items',
        help_text="The product or service being sold/purchased."
    )
    description = models.CharField(max_length=255, blank=True, help_text="Overrides the default item description if needed.")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Price per unit.")

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} x {self.item.name} @ {self.unit_price}"

