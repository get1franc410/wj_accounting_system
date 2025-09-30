# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\customers\models.py

from django.db import models
from apps.core.models import Company
from decimal import Decimal

class Customer(models.Model):
    """
    Represents an entity that can be a Customer, Vendor, or both.
    """
    CUSTOMER = 'customer'
    VENDOR = 'vendor'
    BOTH = 'both'
    ENTITY_TYPE_CHOICES = [
        (CUSTOMER, 'Customer'),
        (VENDOR, 'Vendor'),
        (BOTH, 'Both'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=255, help_text="The full name or company name of the entity.")
    entity_type = models.CharField(
        max_length=10,
        choices=ENTITY_TYPE_CHOICES,
        default=CUSTOMER,
        help_text="Designates whether this entity is a customer, vendor, or both."
    )
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True)
    
    # This field links to the entity's Accounts Receivable ledger.
    receivable_account = models.OneToOneField(
        'accounts.Account', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='customer_receivable',
        help_text="The Accounts Receivable ledger account for this entity."
    )

    # This field links to the entity's Accounts Payable ledger.
    payable_account = models.OneToOneField(
        'accounts.Account', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='customer_payable',
        help_text="The Accounts Payable ledger account for this entity."
    )

    # 🎯 ADD THESE DATABASE FIELDS
    receivable_balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Outstanding amount customer owes to the company"
    )
    
    payable_balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Outstanding amount company owes to the vendor"
    )

    credit_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="The maximum amount of credit to extend to this customer. 0 means no limit."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            ('company', 'name'),
            ('company', 'email'),
            ('company', 'phone'),
        ]
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_calculated_receivable_balance(self):
        """Calculate receivable balance from account ledger"""
        if self.receivable_account:
            return self.receivable_account.get_balance()
        return Decimal('0.00')

    def get_calculated_payable_balance(self):
        """Calculate payable balance from account ledger"""
        if self.payable_account:
            return self.payable_account.get_balance()
        return Decimal('0.00')
    
    def update_balances(self):
        """Update stored balances from transactions"""
        from apps.transactions.models import Transaction
        from decimal import Decimal
        
        # Calculate Receivable Balance (Sales)
        receivable_balance = Decimal('0.00')
        sale_transactions = Transaction.objects.filter(
            customer=self,
            transaction_type='SALE'
        )
        
        for txn in sale_transactions:
            balance_due = txn.total_amount - (txn.amount_paid or Decimal('0.00'))
            receivable_balance += balance_due
        
        # Calculate Payable Balance (Purchases/Expenses)
        payable_balance = Decimal('0.00')
        payable_transactions = Transaction.objects.filter(
            customer=self,
            transaction_type__in=['PURCHASE', 'EXPENSE']
        )
        
        for txn in payable_transactions:
            balance_due = txn.total_amount - (txn.amount_paid or Decimal('0.00'))
            payable_balance += balance_due
        
        self.receivable_balance = receivable_balance
        self.payable_balance = payable_balance
        self.save(update_fields=['receivable_balance', 'payable_balance'])
