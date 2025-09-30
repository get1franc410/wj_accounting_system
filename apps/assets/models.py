# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\assets\models.py
from django.db import models
from django.db.models import Sum
from django.conf import settings
from django.utils import timezone
from apps.core.models import Company 
from decimal import Decimal
from dateutil.relativedelta import relativedelta

class Asset(models.Model):
    class DepreciationMethod(models.TextChoices):
        STRAIGHT_LINE = 'SL', 'Straight-Line'
        DECLINING_BALANCE = 'DB', 'Declining Balance'  # Keep your existing DB option
        DOUBLE_DECLINING = 'DD', 'Double Declining Balance'
        DECLINING_BALANCE_150 = 'DB150', '150% Declining Balance'
        SUM_OF_YEARS = 'SYD', 'Sum of Years Digits'
        UNITS_OF_PRODUCTION = 'UOP', 'Units of Production'
        MACRS = 'MACRS', 'MACRS (US Tax)'
        NO_DEPRECIATION = 'NONE', 'No Depreciation'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='assets')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # For Units of Production method
    estimated_total_units = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Total estimated units of production (for Units of Production method)"
    )
    units_produced_to_date = models.PositiveIntegerField(
        default=0,
        help_text="Total units produced to date"
    )
    
    # --- EXISTING: The expense account for the depreciation journal entry ---
    depreciation_expense_account = models.ForeignKey(
        'accounts.Account', 
        on_delete=models.PROTECT, 
        related_name='asset_depreciation_expenses',
        help_text="The account to debit for depreciation expense."
    )
    asset_account = models.ForeignKey(
        'accounts.Account', 
        on_delete=models.PROTECT, 
        related_name='assets',
        help_text="The primary asset account (e.g., 'Vehicles', 'Machinery')."
    )
    accumulated_depreciation_account = models.ForeignKey(
        'accounts.Account', 
        on_delete=models.PROTECT, 
        related_name='asset_accumulated_depreciation',
        help_text="The contra-asset account to credit for accumulated depreciation."
    )
    
    depreciation_method = models.CharField(
        max_length=10,  # Increased from 2 to accommodate new choices
        choices=DepreciationMethod.choices, 
        default=DepreciationMethod.STRAIGHT_LINE, 
        help_text="Method used to calculate annual depreciation"
    )
    useful_life_years = models.PositiveIntegerField(help_text="The number of years the asset is expected to be in service.")
    salvage_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), help_text="The estimated residual value of an asset at the end of its useful life.")

    def __str__(self):
        return f"{self.name} ({self.company.name})"

    def calculate_annual_depreciation(self, year_number=1, units_produced_this_period=0) -> Decimal:
        """
        Calculates the depreciation amount for a specific year or period.
        
        Args:
            year_number: Which year of the asset's life (1, 2, 3, etc.)
            units_produced_this_period: For units of production method
        """
        if self.depreciation_method == self.DepreciationMethod.NO_DEPRECIATION:
            return Decimal('0.00')
            
        depreciable_base = self.purchase_price - self.salvage_value
        if depreciable_base <= 0 or self.useful_life_years == 0:
            return Decimal('0.00')

        if self.depreciation_method == self.DepreciationMethod.STRAIGHT_LINE:
            # Straight-Line: (Cost - Salvage Value) / Useful Life
            return depreciable_base / Decimal(self.useful_life_years)
        
        elif self.depreciation_method in [self.DepreciationMethod.DECLINING_BALANCE, self.DepreciationMethod.DOUBLE_DECLINING]:
            # Keep backward compatibility with your existing DB method
            # Both DB and DD will use Double Declining Balance (2x rate)
            rate = Decimal('2.0') / Decimal(self.useful_life_years)
            book_value = self.current_book_value
            annual_depreciation = book_value * rate
            # Don't depreciate below salvage value
            return min(annual_depreciation, book_value - self.salvage_value)
        
        elif self.depreciation_method == self.DepreciationMethod.DECLINING_BALANCE_150:
            # 150% Declining Balance: 1.5 * (1 / Useful Life) * Book Value
            rate = Decimal('1.5') / Decimal(self.useful_life_years)
            book_value = self.current_book_value
            annual_depreciation = book_value * rate
            return min(annual_depreciation, book_value - self.salvage_value)
        
        elif self.depreciation_method == self.DepreciationMethod.SUM_OF_YEARS:
            # Sum of Years Digits: (Remaining Life / Sum of Years) * Depreciable Base
            sum_of_years = sum(range(1, self.useful_life_years + 1))
            remaining_years = self.useful_life_years - year_number + 1
            if remaining_years <= 0:
                return Decimal('0.00')
            return (Decimal(remaining_years) / Decimal(sum_of_years)) * depreciable_base
        
        elif self.depreciation_method == self.DepreciationMethod.UNITS_OF_PRODUCTION:
            # Units of Production: (Units Produced / Total Estimated Units) * Depreciable Base
            if not self.estimated_total_units or self.estimated_total_units == 0:
                return Decimal('0.00')
            
            rate_per_unit = depreciable_base / Decimal(self.estimated_total_units)
            return rate_per_unit * Decimal(units_produced_this_period)
        
        elif self.depreciation_method == self.DepreciationMethod.MACRS:
            # MACRS - Simplified 5-year property schedule
            macrs_rates = {
                1: Decimal('0.20'),    # 20%
                2: Decimal('0.32'),    # 32%
                3: Decimal('0.192'),   # 19.2%
                4: Decimal('0.1152'),  # 11.52%
                5: Decimal('0.1152'),  # 11.52%
                6: Decimal('0.0576'),  # 5.76%
            }
            
            if year_number in macrs_rates:
                return self.purchase_price * macrs_rates[year_number]
            return Decimal('0.00')

        return Decimal('0.00')

    def get_accumulated_depreciation(self) -> Decimal:
        """
        Calculates total depreciation by summing up all related depreciation entries.
        This is the source of truth for posted depreciation.
        """
        total = self.depreciation_entries.aggregate(total_amount=Sum('amount'))['total_amount']
        return total or Decimal('0.00')

    @property
    def current_book_value(self) -> Decimal:
        """
        Calculates the current book value of the asset.
        Book Value = Original Purchase Price - Accumulated Depreciation.
        """
        return self.purchase_price - self.get_accumulated_depreciation()

    @property
    def total_maintenance_cost(self) -> Decimal:
        """This will sum up the cost of all maintenance records for this asset."""
        total = self.maintenance_records.aggregate(total_cost=Sum('cost'))['total_cost']
        return total or Decimal('0.00')

# --- EXISTING MODEL TO TRACK MAINTENANCE ---
class AssetMaintenance(models.Model):
    class MaintenanceType(models.TextChoices):
        REPAIR = 'REPAIR', 'Repair'
        ROUTINE = 'ROUTINE', 'Routine Service'
        UPGRADE = 'UPGRADE', 'Upgrade'

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='maintenance_records')
    maintenance_date = models.DateField()
    maintenance_type = models.CharField(max_length=10, choices=MaintenanceType.choices)
    description = models.TextField(help_text="Describe the work that was done.")
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.maintenance_type} for {self.asset.name} on {self.maintenance_date}"

# --- ENHANCED MODEL TO CREATE AN AUDIT TRAIL FOR DEPRECIATION ---
class DepreciationEntry(models.Model):
    """
    Records a successful depreciation posting for an asset for a specific period.
    This prevents duplicate postings and creates a clear history.
    """
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='depreciation_entries')
    journal_entry = models.OneToOneField(
        'journal.JournalEntry', 
        on_delete=models.PROTECT, 
        related_name='depreciation_record'
    )
    date = models.DateField(help_text="The date for which depreciation was calculated (e.g., end of the month).")
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="The amount of depreciation posted for this period.")
    year_number = models.PositiveIntegerField(default=1, help_text="Which year of the asset's life")
    units_produced = models.PositiveIntegerField(default=0, help_text="Units produced this period (for UOP method)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Depreciation Entries"
        ordering = ['-date']
        unique_together = ('asset', 'date') # Ensures only one entry per asset per day

    def __str__(self):
        return f"Depreciation for {self.asset.name} on {self.date} for {self.amount}"
