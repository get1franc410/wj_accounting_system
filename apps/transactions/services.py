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

@db_transaction.atomic
def create_journal_entry_for_transaction(transaction_instance):
    """
    🔧 FIXED & ENHANCED VERSION
    - Creates journal entries for all transaction types.
    - Handles both inventory line items and expense splits.
    - Keeps all existing inventory management and COGS logic.
    """
    company = transaction_instance.company
    total_amount = round_currency(transaction_instance.total_amount)
    amount_paid = round_currency(transaction_instance.amount_paid or Decimal('0.00'))

    # Delete any previous journal entry to ensure a clean slate
    JournalEntry.objects.filter(
        company=company,
        description__contains=f"Transaction #{transaction_instance.id}"
    ).delete()

    # Unlink from the transaction object itself
    transaction_instance.journal_entry = None
    transaction_instance.save(update_fields=['journal_entry'])

    # Do not create a journal entry for zero-value transactions
    if total_amount <= 0:
        return None 

    try:
        # Create the main Journal Entry record
        je = JournalEntry.objects.create(
            company=company,
            date=transaction_instance.date,
            description=f"{transaction_instance.get_transaction_type_display()} - Transaction #{transaction_instance.id}",
            created_by=getattr(transaction_instance, 'created_by', None)
        )
        
        # Link the new journal entry back to the transaction
        transaction_instance.journal_entry = je
        transaction_instance.save(update_fields=['journal_entry'])

        # Get system accounts with improved error handling
        cash_account = get_cash_account(company)
        if not cash_account:
            raise ValidationError("No cash/bank account found for this company.")

        # Determine if the transaction uses inventory line items or expense splits
        has_line_items = transaction_instance.items.exists()

        # --- 1. SALE LOGIC (No changes here, remains as is) ---
        if transaction_instance.transaction_type == 'SALE':
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

            # Credit side (Income) and COGS
            total_cogs = Decimal('0.00')
            
            if has_line_items:
                for line_item in transaction_instance.items.all():
                    income_account = line_item.item.income_account
                    if not income_account:
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

                    # --- INVENTORY MOVEMENT ---
                    if line_item.item.is_product:
                        InventoryTransaction.objects.create(
                            company=company, item=line_item.item,
                            transaction_type=InventoryTransaction.SALE,
                            quantity=line_item.quantity,
                            transaction_date=transaction_instance.date,
                            notes=f"Sale via Transaction #{transaction_instance.id}"
                        )
                        line_item.item.quantity_on_hand -= line_item.quantity
                        line_item.item.save(update_fields=['quantity_on_hand'])
                        
                        item_cost = getattr(line_item.item, 'current_average_cost', line_item.item.purchase_price or Decimal('0.00'))
                        total_cogs += round_currency(item_cost * line_item.quantity)
            else:
                if not transaction_instance.category or not transaction_instance.category.default_account:
                    raise ValidationError("A category with a linked default account is required for simple sales.")
                revenue_account = transaction_instance.category.default_account
                JournalEntryLine.objects.create(
                    journal_entry=je, account=revenue_account, 
                    debit=Decimal('0.00'), credit=total_amount,
                    description=f"Sales revenue from {transaction_instance.description or 'simple sale'}"
                )

            # COGS Entry
            if total_cogs > 0:
                try:
                    cogs_account = Account.objects.get(company=company, system_account=Account.SystemAccount.COST_OF_GOODS_SOLD)
                    inventory_asset_account = Account.objects.get(company=company, system_account=Account.SystemAccount.INVENTORY_ASSET)
                    JournalEntryLine.objects.create(
                        journal_entry=je, account=cogs_account, 
                        debit=total_cogs, credit=Decimal('0.00'),
                        description="Cost of goods sold"
                    )
                    JournalEntryLine.objects.create(
                        journal_entry=je, account=inventory_asset_account, 
                        debit=Decimal('0.00'), credit=total_cogs,
                        description="Inventory reduction"
                    )
                except Account.DoesNotExist:
                    pass

        elif transaction_instance.transaction_type == 'PURCHASE':
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

            # Debit side (what was purchased)
            if has_line_items: 
                for line_item in transaction_instance.items.all():
                    if line_item.item.is_product:
                        asset_account = line_item.item.asset_account
                        if not asset_account:
                            try:
                                asset_account = Account.objects.get(company=company, system_account=Account.SystemAccount.INVENTORY_ASSET)
                            except Account.DoesNotExist:
                                raise ValidationError("No inventory asset account found")
                        
                        JournalEntryLine.objects.create(
                            journal_entry=je, account=asset_account, 
                            debit=round_currency(line_item.line_total), credit=Decimal('0.00'),
                            description=f"Purchase of {line_item.item.name}"
                        )
                        
                        InventoryTransaction.objects.create(
                            company=company, item=line_item.item,
                            transaction_type=InventoryTransaction.PURCHASE,
                            quantity=line_item.quantity,
                            transaction_date=transaction_instance.date,
                            notes=f"Purchase via Transaction #{transaction_instance.id}"
                        )
                        line_item.item.quantity_on_hand += line_item.quantity
                        line_item.item.save(update_fields=['quantity_on_hand'])
                    else: # Service
                        expense_account = line_item.item.expense_account
                        if not expense_account:
                            expense_account = get_expense_account(company)
                            if not expense_account:
                                raise ValidationError("No expense account found")
                        
                        JournalEntryLine.objects.create(
                            journal_entry=je, account=expense_account, 
                            debit=round_currency(line_item.line_total), credit=Decimal('0.00'),
                            description=f"Purchase of {line_item.item.name}"
                        )
            else: 
                for line in transaction_instance.expense_lines.all():
                    JournalEntryLine.objects.create(
                        journal_entry=je, 
                        account=line.account, 
                        debit=round_currency(line.amount), 
                        credit=Decimal('0.00'),
                        description=line.description or f"Purchase allocation to {line.account.name}"
                    )
        elif transaction_instance.transaction_type == 'EXPENSE':
            if total_amount > 0:
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=cash_account, 
                    debit=Decimal('0.00'), 
                    credit=total_amount,
                    description="Cash payment for expense"
                )

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

                    if line_item.item.item_type == InventoryItem.PRODUCT:
                        InventoryTransaction.objects.create(
                            company=company, item=line_item.item,
                            transaction_type=InventoryTransaction.ADJUSTMENT_OUT,
                            quantity=line_item.quantity,
                            transaction_date=transaction_instance.date,
                            notes=f"Stock out via Expense Transaction #{transaction_instance.id}"
                        )
                        line_item.item.quantity_on_hand -= line_item.quantity
                        line_item.item.save(update_fields=['quantity_on_hand'])
            else: 
                for line in transaction_instance.expense_lines.all():
                    JournalEntryLine.objects.create(
                        journal_entry=je, 
                        account=line.account, 
                        debit=round_currency(line.amount), 
                        credit=Decimal('0.00'),
                        description=line.description or f"Expense allocation to {line.account.name}"
                    )
        elif transaction_instance.transaction_type in ['PAYMENT', 'Payment Receipt']:
            try:
                ar_account = Account.objects.get(
                    company=company,
                    system_account=Account.SystemAccount.ACCOUNTS_RECEIVABLE
                )
            except Account.DoesNotExist:
                raise ValidationError("Accounts Receivable system account not found")
            
            if total_amount > 0:
                JournalEntryLine.objects.create(
                    journal_entry=je, 
                    account=cash_account, 
                    debit=total_amount, 
                    credit=Decimal('0.00'),
                    description=f"Payment received from {transaction_instance.customer.name if transaction_instance.customer else 'Customer'}"
                )
            
            JournalEntryLine.objects.create(
                journal_entry=je, 
                account=ar_account, 
                debit=Decimal('0.00'), 
                credit=total_amount,
                description=f"Payment from {transaction_instance.customer.name if transaction_instance.customer else 'Customer'}"
            )

        je.validate_balance()
            
        return je

    except Exception as e:
        if 'je' in locals() and je.pk:
            je.delete()
        transaction_instance.journal_entry = None
        transaction_instance.save(update_fields=['journal_entry'])
        raise ValidationError(f"Error creating journal entry: {str(e)}")