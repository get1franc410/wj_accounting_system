# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\assets\services.py
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import Asset, DepreciationEntry
from apps.journal.models import JournalEntry, JournalEntryLine

def post_depreciation_for_asset(asset: Asset, post_date: timezone.datetime.date) -> tuple[JournalEntry | None, str]:
    """
    Calculates monthly depreciation and creates a corresponding journal entry.
    Checks to prevent duplicate entries for the same month.

    Args:
        asset: The Asset instance to depreciate.
        post_date: The date for which to post the depreciation (typically month-end).

    Returns:
        A tuple containing the created JournalEntry (or None) and a status message.
    """
    # 1. Validation Checks
    if post_date < asset.purchase_date:
        return None, "Post date cannot be before the asset's purchase date."

    # Check if depreciation has already been posted for this asset for the given month and year
    if DepreciationEntry.objects.filter(asset=asset, date__year=post_date.year, date__month=post_date.month).exists():
        return None, f"Depreciation for {post_date.strftime('%B %Y')} has already been posted for {asset.name}."

    # 2. Calculate Monthly Depreciation
    annual_depreciation = asset.calculate_annual_depreciation()
    monthly_depreciation = (annual_depreciation / Decimal('12')).quantize(Decimal('0.01'))

    if monthly_depreciation <= 0:
        return None, "Calculated monthly depreciation is zero or less. No entry posted."
    
    # Ensure we don't depreciate below salvage value
    book_value = asset.current_book_value
    if book_value - monthly_depreciation < asset.salvage_value:
        monthly_depreciation = book_value - asset.salvage_value
        if monthly_depreciation <= 0:
            return None, "Asset has reached its salvage value. No further depreciation."

    # 3. Create Journal Entry within a Transaction
    try:
        with transaction.atomic():
            # Create the main Journal Entry
            je = JournalEntry.objects.create(
                company=asset.company,
                date=post_date,
                description=f"Monthly depreciation for asset: {asset.name}",
                # You can add a field to JournalEntry like 'source' or 'type'
                # to mark it as system-generated, e.g., source='assets_module'
            )

            # Create the Debit Line (Depreciation Expense)
            JournalEntryLine.objects.create(
                journal_entry=je,
                account=asset.depreciation_expense_account,
                debit=monthly_depreciation,
                credit=Decimal('0.00')
            )

            # Create the Credit Line (Accumulated Depreciation)
            JournalEntryLine.objects.create(
                journal_entry=je,
                account=asset.accumulated_depreciation_account,
                debit=Decimal('0.00'),
                credit=monthly_depreciation
            )

            # 4. Create the Audit Record in the DepreciationEntry table
            DepreciationEntry.objects.create(
                asset=asset,
                journal_entry=je,
                date=post_date,
                amount=monthly_depreciation
            )

        return je, f"Successfully posted depreciation of {monthly_depreciation} for {asset.name}."

    except Exception as e:
        # Handle potential database errors
        return None, f"An error occurred: {str(e)}"

