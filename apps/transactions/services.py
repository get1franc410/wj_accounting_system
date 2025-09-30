# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\transactions\services.py
from decimal import Decimal
from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from apps.journal.models import JournalEntry, JournalEntryLine
from apps.inventory.models import InventoryTransaction, InventoryItem
from apps.accounts.models import Account, AccountType
from apps.transactions.constants import TransactionType

def round_currency(amount):
    """Round amount to 2 decimal places consistently"""
    from decimal import ROUND_HALF_UP
    if amount is None:
        return Decimal('0.00')
    return Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def get_cash_account(company):
    """Get default cash account"""
    try:
        return Account.objects.get(
            company=company,
            system_account=Account.SystemAccount.DEFAULT_CASH
        )
    except Account.DoesNotExist:
        return Account.objects.filter(
            company=company,
            account_type__name__icontains='Bank'
        ).first()

def get_revenue_account(company):
    """Get default revenue account"""
    try:
        return Account.objects.get(
            company=company,
            system_account=Account.SystemAccount.SALES_REVENUE
        )
    except Account.DoesNotExist:
        return Account.objects.filter(
            company=company,
            account_type__category=AccountType.Category.REVENUE
        ).first()

def get_expense_account(company):
    """Get default expense account"""
    return Account.objects.filter(
        company=company,
        account_type__category=AccountType.Category.EXPENSE
    ).first()

# UPDATED MAIN FUNCTION
@db_transaction.atomic
def create_journal_entry_for_transaction(transaction_instance):
    """
    🔧 FIXED VERSION - Addresses negative balances and unbalanced sheets
    Keeps all existing inventory management logic
    """
    company = transaction_instance.company
    total_amount = round_currency(transaction_instance.total_amount)
    amount_paid = round_currency(transaction_instance.amount_paid or Decimal('0.00'))

    # DELETE EXISTING JOURNAL ENTRIES FOR THIS TRANSACTION (IMPROVED)
    JournalEntry.objects.filter(
        company=company,
        description__contains=f"Transaction #{transaction_instance.id}"
    ).delete()

    # RESET THE JOURNAL ENTRY REFERENCE
    transaction_instance.journal_entry = None
    transaction_instance.save(update_fields=['journal_entry'])

    if total_amount <= 0:
        return None  # No journal entry for zero amount transactions

    try:
        # CREATE NEW JOURNAL ENTRY WITH BETTER DESCRIPTION
        je = JournalEntry.objects.create(
            company=company,
            date=transaction_instance.date,
            description=f"{transaction_instance.get_transaction_type_display()} - Transaction #{transaction_instance.id}",
            created_by=getattr(transaction_instance, 'created_by', None)
        )
        
        # LINK THE JOURNAL ENTRY TO THE TRANSACTION
        transaction_instance.journal_entry = je
        transaction_instance.save(update_fields=['journal_entry'])

        # Get system accounts with improved error handling
        cash_account = get_cash_account(company)
        if not cash_account:
            raise ValidationError("No cash/bank account found for this company.")

        has_line_items = transaction_instance.items.exists()

        # --- 1. SALE LOGIC (FIXED) ---
        if transaction_instance.transaction_type == 'SALE':
            # 🔧 FIX: Use system accounts instead of customer-specific accounts
            try:
                ar_account = Account.objects.get(
                    company=company,
                    system_account=Account.SystemAccount.ACCOUNTS_RECEIVABLE
                )
            except Account.DoesNotExist:
                raise ValidationError("Accounts Receivable system account not found")
            
            # Debit side (Cash and/or Accounts Receivable)
            if amount_paid > 0:
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=cash_account, 
                    debit=amount_paid, 
                    credit=Decimal('0.00'),
                    description=f"Cash received from {transaction_instance.customer.name if transaction_instance.customer else 'Customer'}"
                )
            
            amount_due = total_amount - amount_paid
            if amount_due > 0:
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=ar_account, 
                    debit=amount_due, 
                    credit=Decimal('0.00'),
                    description=f"Sale to {transaction_instance.customer.name if transaction_instance.customer else 'Customer'}"
                )

            # Credit side (Income) and COGS - KEEP YOUR EXISTING LOGIC
            total_cogs = Decimal('0.00')
            
            if has_line_items:
                for line_item in transaction_instance.items.all():
                    income_account = line_item.item.income_account
                    if not income_account:
                        # Fallback to default revenue account
                        income_account = get_revenue_account(company)
                        if not income_account:
                            raise ValidationError("No revenue account available")
                    
                    JournalEntryLine.objects.create(
                        journal_entry=je, 
                        account=income_account, 
                        debit=Decimal('0.00'), 
                        credit=round_currency(line_item.line_total),
                        description=f"Sale of {line_item.item.name}"
                    )

                    # --- INVENTORY MOVEMENT (KEEP YOUR EXISTING LOGIC) ---
                    if line_item.item.item_type == InventoryItem.PRODUCT:
                        # Create inventory transaction (stock out)
                        InventoryTransaction.objects.create(
                            company=company,
                            item=line_item.item,
                            transaction_type=InventoryTransaction.SALE,
                            quantity=line_item.quantity,
                            transaction_date=transaction_instance.date,
                            notes=f"Sale via Transaction #{transaction_instance.id}"
                        )
                        # Update stock
                        line_item.item.quantity_on_hand -= line_item.quantity
                        line_item.item.save(update_fields=['quantity_on_hand'])
                        
                        # 🔧 FIX: Use current_average_cost if available, otherwise purchase_price
                        item_cost = getattr(line_item.item, 'current_average_cost', line_item.item.purchase_price or Decimal('0.00'))
                        total_cogs += round_currency(item_cost * line_item.quantity)
            else:
                # Simple sale without line items
                if not transaction_instance.category or not transaction_instance.category.default_account:
                    raise ValidationError(
                        "A category with a linked default account is required for simple sales."
                    )
                
                revenue_account = transaction_instance.category.default_account
                
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=revenue_account, 
                    debit=Decimal('0.00'), 
                    credit=total_amount,
                    description=f"Sales revenue from {transaction_instance.description or 'simple sale'}"
                )

            # COGS Entry (KEEP YOUR EXISTING LOGIC)
            if total_cogs > 0:
                try:
                    cogs_account = Account.objects.get(company=company, system_account=Account.SystemAccount.COST_OF_GOODS_SOLD)
                    inventory_asset_account = Account.objects.get(company=company, system_account=Account.SystemAccount.INVENTORY_ASSET)
                    JournalEntryLine.objects.create(
                        journal_entry=je, 
                        account=cogs_account, 
                        debit=total_cogs, 
                        credit=Decimal('0.00'),
                        description="Cost of goods sold"
                    )
                    JournalEntryLine.objects.create(
                        journal_entry=je, 
                        account=inventory_asset_account, 
                        debit=Decimal('0.00'), 
                        credit=total_cogs,
                        description="Inventory reduction"
                    )
                except Account.DoesNotExist:
                    pass

        # --- 2. PURCHASE LOGIC (FIXED) ---
        elif transaction_instance.transaction_type == 'PURCHASE':
            # 🔧 FIX: Use system accounts
            try:
                ap_account = Account.objects.get(
                    company=company,
                    system_account=Account.SystemAccount.ACCOUNTS_PAYABLE
                )
            except Account.DoesNotExist:
                raise ValidationError("Accounts Payable system account not found")
            
            # Credit side (Cash and/or Accounts Payable)
            if amount_paid > 0:
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=cash_account, 
                    debit=Decimal('0.00'), 
                    credit=amount_paid,
                    description=f"Payment to {transaction_instance.customer.name if transaction_instance.customer else 'Vendor'}"
                )
            
            amount_owed = total_amount - amount_paid
            if amount_owed > 0:
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=ap_account, 
                    debit=Decimal('0.00'), 
                    credit=amount_owed,
                    description=f"Purchase from {transaction_instance.customer.name if transaction_instance.customer else 'Vendor'}"
                )

            # Debit side (what was purchased) - KEEP YOUR EXISTING LOGIC
            if has_line_items:
                for line_item in transaction_instance.items.all():
                    if line_item.item.item_type == InventoryItem.PRODUCT:
                        asset_account = line_item.item.asset_account
                        if not asset_account:
                            # Fallback to system inventory account
                            try:
                                asset_account = Account.objects.get(company=company, system_account=Account.SystemAccount.INVENTORY_ASSET)
                            except Account.DoesNotExist:
                                raise ValidationError("No inventory asset account found")
                        
                        JournalEntryLine.objects.create(
                            journal_entry=je, 
                            account=asset_account, 
                            debit=round_currency(line_item.line_total), 
                            credit=Decimal('0.00'),
                            description=f"Purchase of {line_item.item.name}"
                        )
                        
                        # --- INVENTORY MOVEMENT (KEEP YOUR EXISTING LOGIC) ---
                        InventoryTransaction.objects.create(
                            company=company,
                            item=line_item.item,
                            transaction_type=InventoryTransaction.PURCHASE,
                            quantity=line_item.quantity,
                            transaction_date=transaction_instance.date,
                            notes=f"Purchase via Transaction #{transaction_instance.id}"
                        )
                        # Update stock
                        line_item.item.quantity_on_hand += line_item.quantity
                        line_item.item.save(update_fields=['quantity_on_hand'])
                    else: # Service
                        expense_account = line_item.item.expense_account
                        if not expense_account:
                            expense_account = get_expense_account(company)
                            if not expense_account:
                                raise ValidationError("No expense account found")
                        
                        JournalEntryLine.objects.create(
                            journal_entry=je, 
                            account=expense_account, 
                            debit=round_currency(line_item.line_total), 
                            credit=Decimal('0.00'),
                            description=f"Purchase of {line_item.item.name}"
                        )
            else:
                # Simple purchase (no line items)
                if transaction_instance.category and transaction_instance.category.default_account:
                    purchase_account = transaction_instance.category.default_account
                else:
                    # Fallback to inventory account
                    try:
                        purchase_account = Account.objects.get(company=company, system_account=Account.SystemAccount.INVENTORY_ASSET)
                    except Account.DoesNotExist:
                        purchase_account = get_expense_account(company)
                        if not purchase_account:
                            raise ValidationError("No purchase account found")
                
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=purchase_account, 
                    debit=total_amount, 
                    credit=Decimal('0.00'),
                    description="Purchase"
                )

        # --- 3. EXPENSE LOGIC (KEEP YOUR EXISTING LOGIC) ---
        elif transaction_instance.transaction_type == 'EXPENSE':
            # Credit side (Cash)
            if total_amount > 0:
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=cash_account, 
                    debit=Decimal('0.00'), 
                    credit=total_amount,
                    description="Cash payment for expense"
                )

            # Debit side (what was expensed) - KEEP YOUR EXISTING LOGIC
            if has_line_items:
                for line_item in transaction_instance.items.all():
                    expense_account = line_item.item.expense_account
                    if not expense_account:
                        expense_account = get_expense_account(company)
                        if not expense_account:
                            raise ValidationError("No expense account found")
                    
                    JournalEntryLine.objects.create(
                        journal_entry=je, 
                        account=expense_account, 
                        debit=round_currency(line_item.line_total), 
                        credit=Decimal('0.00'),
                        description=f"Expense for {line_item.item.name}"
                    )

                    # --- INVENTORY MOVEMENT for EXPENSE (KEEP YOUR EXISTING LOGIC) ---
                    if line_item.item.item_type == InventoryItem.PRODUCT:
                        InventoryTransaction.objects.create(
                            company=company,
                            item=line_item.item,
                            transaction_type=InventoryTransaction.ADJUSTMENT_OUT,
                            quantity=line_item.quantity,
                            transaction_date=transaction_instance.date,
                            notes=f"Stock out via Expense Transaction #{transaction_instance.id}"
                        )
                        line_item.item.quantity_on_hand -= line_item.quantity
                        line_item.item.save(update_fields=['quantity_on_hand'])
            else:
                if transaction_instance.category and transaction_instance.category.default_account:
                    expense_account = transaction_instance.category.default_account
                else:
                    expense_account = get_expense_account(company)
                    if not expense_account:
                        raise ValidationError("No expense account found")
                
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=expense_account, 
                    debit=total_amount, 
                    credit=Decimal('0.00'),
                    description="General expense"
                )

        # --- 4. PAYMENT/RECEIPT LOGIC (FIXED) ---
        elif transaction_instance.transaction_type in ['PAYMENT', 'Payment Receipt']:
            # 🔧 FIX: Use system AR account
            try:
                ar_account = Account.objects.get(
                    company=company,
                    system_account=Account.SystemAccount.ACCOUNTS_RECEIVABLE
                )
            except Account.DoesNotExist:
                raise ValidationError("Accounts Receivable system account not found")
            
            # Debit: Cash (payment received)
            if total_amount > 0:
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=cash_account, 
                    debit=total_amount, 
                    credit=Decimal('0.00'),
                    description=f"Payment received from {transaction_instance.customer.name if transaction_instance.customer else 'Customer'}"
                )
            
            # Credit: Accounts Receivable (reduce customer balance)
            JournalEntryLine.objects.create(
                journal_entry=je, 
                account=ar_account, 
                debit=Decimal('0.00'), 
                credit=total_amount,
                description=f"Payment from {transaction_instance.customer.name if transaction_instance.customer else 'Customer'}"
            )

        # FINAL VALIDATION TO ENSURE THE ENTRY IS BALANCED
        je.validate_balance()
            
        return je

    except Exception as e:
        # Clean up if there's an error
        if 'je' in locals():
            je.delete()
        transaction_instance.journal_entry = None
        transaction_instance.save(update_fields=['journal_entry'])
        raise ValidationError(f"Error creating journal entry: {str(e)}")