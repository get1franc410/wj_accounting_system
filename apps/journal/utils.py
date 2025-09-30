# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\journal\utils.py

from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import JournalEntry
from apps.accounts.models import Account
from apps.inventory.models import InventoryTransaction

@transaction.atomic
def create_journal_entry_for_inventory_transaction(inventory_tx: InventoryTransaction):
    """
    Creates a balanced journal entry for inventory transactions with proper rounding
    """
    from decimal import ROUND_HALF_UP
    
    def round_currency(amount):
        """Round amount to 2 decimal places consistently"""
        if amount is None:
            return Decimal('0.00')
        return Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    item = inventory_tx.item
    company = inventory_tx.company
    
    print(f"DEBUG: Processing inventory transaction for {item.name}")
    print(f"DEBUG: Transaction type: {inventory_tx.transaction_type}")
    print(f"DEBUG: Quantity: {inventory_tx.quantity}")
    
    # Check required accounts
    if not item.asset_account:
        print(f"DEBUG: No asset account for item {item.name}")
        return None
        
    if not item.expense_account:
        print(f"DEBUG: No expense account for item {item.name}")
        return None

    # Calculate total value with proper rounding
    unit_price = round_currency(item.purchase_price)
    quantity = Decimal(str(inventory_tx.quantity))
    total_value = round_currency(unit_price * quantity)
    
    print(f"DEBUG: Calculated total value: {total_value}")
    
    if total_value <= 0:
        print(f"DEBUG: Total value is zero or negative: {total_value}")
        return None

    # Create journal entry with proper description
    je_description = f"Inventory {inventory_tx.get_transaction_type_display()}: {item.name}"

    journal_entry = JournalEntry.objects.create(
        company=company,
        date=inventory_tx.transaction_date.date() if hasattr(inventory_tx.transaction_date, 'date') else inventory_tx.transaction_date,
        description=je_description
    )

    debit_account = None
    credit_account = None

    # Handle different transaction types
    if inventory_tx.transaction_type in InventoryTransaction.get_stock_decrease_types():
        # Stock decrease: Debit Expense, Credit Asset
        debit_account = item.expense_account
        credit_account = item.asset_account
        print(f"DEBUG: Stock decrease - Debit: {debit_account}, Credit: {credit_account}")

    elif inventory_tx.transaction_type == InventoryTransaction.PURCHASE:
        # Purchase: Debit Asset, Credit Accounts Payable
        debit_account = item.asset_account
        
        try:
            credit_account = Account.objects.get(
                company=company,
                system_account=Account.SystemAccount.ACCOUNTS_PAYABLE
            )
            print(f"DEBUG: Purchase - Debit: {debit_account}, Credit: {credit_account}")
        except Account.DoesNotExist:
            try:
                credit_account = Account.objects.get(
                    company=company,
                    account_number='2200'
                )
                print(f"DEBUG: Using fallback account 2200")
            except Account.DoesNotExist:
                print("DEBUG: No suitable accounts payable account found")
                journal_entry.delete()
                return None

    else:
        # Other adjustments: Debit Asset, Credit Expense
        debit_account = item.asset_account
        credit_account = item.expense_account
        print(f"DEBUG: Other adjustment - Debit: {debit_account}, Credit: {credit_account}")

    # Create balanced journal entry lines with proper rounding
    if debit_account and credit_account and total_value > 0:
        print(f"DEBUG: Creating journal lines with amount: {total_value}")
        
        # Debit line
        journal_entry.lines.create(
            account=debit_account,
            debit=total_value,  # Already rounded
            credit=Decimal('0.00'),
            description=f"{inventory_tx.get_transaction_type_display()} - {item.name}"
        )
        
        # Credit line
        journal_entry.lines.create(
            account=credit_account,
            debit=Decimal('0.00'),
            credit=total_value,  # Already rounded
            description=f"{inventory_tx.get_transaction_type_display()} - {item.name}"
        )
        
        # Validate the entry with improved tolerance
        try:
            journal_entry.validate_balance()
            print(f"DEBUG: Journal entry created and validated successfully with ID: {journal_entry.id}")
            return journal_entry
        except ValidationError as e:
            print(f"DEBUG: Journal entry validation failed: {e}")
            journal_entry.delete()
            return None
    else:
        print("DEBUG: Invalid accounts or zero amount, deleting journal entry")
        journal_entry.delete()
        return None