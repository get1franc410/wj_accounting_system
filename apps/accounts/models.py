# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\accounts\models.py

from django.db import models
from django.db.models import Sum
from decimal import Decimal
from mptt.models import MPTTModel, TreeForeignKey
from apps.core.models import Company
from django.utils.translation import gettext_lazy as _
from apps.journal.models import JournalEntryLine

class AccountType(models.Model):
    class Category(models.TextChoices):
        ASSET = 'ASSET', _('Asset')
        LIABILITY = 'LIABILITY', _('Liability')
        EQUITY = 'EQUITY', _('Equity')
        REVENUE = 'REVENUE', _('Revenue')
        EXPENSE = 'EXPENSE', _('Expense')

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        default=Category.ASSET
    )

    def __str__(self):
        return self.name

class Account(MPTTModel):
    # --- Choices for special system accounts ---
    class SystemAccount(models.TextChoices):
        COST_OF_GOODS_SOLD = 'COGS', _('Cost of Goods Sold')
        DEFAULT_CASH = 'CASH', _('Default Cash/Bank')
        INVENTORY_ASSET = 'INVENTORY', _('Inventory Asset')
        ACCOUNTS_RECEIVABLE = 'AR', _('Accounts Receivable')
        ACCOUNTS_PAYABLE = 'AP', _('Accounts Payable')
        RETAINED_EARNINGS = 'RETAINED_EARNINGS', _('Retained Earnings')
        SALES_TAX_PAYABLE = 'SALES_TAX', _('Sales Tax Payable')

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='accounts')
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT, related_name='accounts')
    name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20, help_text=_("The unique number for this account (e.g., 1110, 4100)."))
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', help_text=_("The parent account in the hierarchy."))
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_control_account = models.BooleanField(default=False, help_text=_("True if this is a control account like Accounts Receivable or Accounts Payable."))
    
    # --- The new system_account field ---
    system_account = models.CharField(
        max_length=20,
        choices=SystemAccount.choices,
        null=True,
        blank=True,
        help_text=_("Designates this account for a special system purpose (e.g., COGS, Accounts Receivable).")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class MPTTMeta:
        order_insertion_by = ['account_number']

    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        # --- COMBINED UNIQUENESS ---
        # An account number must be unique for a company.
        # A system account designation (if set) must also be unique for a company.
        unique_together = [
            ('company', 'account_number'),
            ('company', 'system_account')
        ]
        ordering = ['account_number']

    def __str__(self):
        return f"{self.account_number} - {self.name}"

    def get_balance(self):
        """
        Calculates the balance of the account by summing its journal entry lines.
        This method now correctly considers all child accounts in the hierarchy.
        """
        # Get this account and all of its descendants
        accounts = self.get_descendants(include_self=True)
        
        # Aggregate journal lines for all these accounts
        sums = JournalEntryLine.objects.filter(account__in=accounts).aggregate(
            total_debit=Sum('debit', default=Decimal('0.00')),
            total_credit=Sum('credit', default=Decimal('0.00'))
        )
        total_debit = sums['total_debit']
        total_credit = sums['total_credit']

        if self.account_type.category in [self.account_type.Category.ASSET, self.account_type.Category.EXPENSE]:
            return total_debit - total_credit
        else:
            return total_credit - total_debit
            
    # We need to import here to avoid circular dependency issues at startup
    @property
    def journal_lines(self):
        from apps.journal.models import JournalEntryLine
        return JournalEntryLine.objects.filter(account=self)

