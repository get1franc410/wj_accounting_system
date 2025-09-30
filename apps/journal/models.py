# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\journal\models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models import Sum # <-- Add this import
from decimal import Decimal # <-- Add this import
from apps.core.models import Company

class JournalEntry(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='journal_entries'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journal_entries_created'
    )
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Journal Entry")
        verbose_name_plural = _("Journal Entries")
        ordering = ['-date']

    def __str__(self):
        return f"JE-{self.id} on {self.date}: {self.description}"

    # --- ADD THIS ENTIRE METHOD ---
    def validate_balance(self):
        """
        Validates that the sum of debits equals the sum of credits for all lines
        and that the total is not zero. Allows small rounding differences.
        Raises a ValidationError if the entry is unbalanced or has a zero total.
        """
        from decimal import ROUND_HALF_UP
        
        # Use database aggregation to get the sums efficiently
        totals = self.lines.aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        
        total_debits = totals.get('total_debit') or Decimal('0.00')
        total_credits = totals.get('total_credit') or Decimal('0.00')

        # Round both totals to 2 decimal places for comparison
        total_debits = total_debits.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_credits = total_credits.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if total_debits == Decimal('0.00') and total_credits == Decimal('0.00'):
            raise ValidationError("A journal entry cannot have a zero balance.")

        # Allow small rounding differences (up to 1 cent)
        difference = abs(total_debits - total_credits)
        tolerance = Decimal('0.01')
        
        if difference > tolerance:
            raise ValidationError([
                f"The journal entry is unbalanced. "
                f"Debits ({total_debits}) do not equal Credits ({total_credits}). "
                f"Difference: {total_debits - total_credits}"
            ])
    
    @property
    def total_amount(self):
        """Calculate total debit amount (which equals total credit amount)"""
        return sum(line.debit for line in self.lines.all())
    
class JournalEntryLine(models.Model):
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.PROTECT,
        related_name='journal_lines'
    )
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Line for JE-{self.journal_entry.id} - {self.account}"