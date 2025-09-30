# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\reporting\utils.py

import os
import csv
import zipfile
from io import StringIO
from django.conf import settings
from django.utils import timezone
from django.db.models import Q

# Import all relevant models
from apps.accounts.models import Account
from apps.journal.models import JournalEntry, JournalEntryLine
from apps.transactions.models import Transaction, TransactionItem
from apps.customers.models import Customer
from apps.inventory.models import InventoryItem, InventoryTransaction
from apps.assets.models import Asset, AssetMaintenance, DepreciationEntry

def export_all_data_to_zip(company, start_date=None, end_date=None, incremental=False, last_backup_date=None):
    """
    Exports key company data to a series of CSV files with date range and incremental support.
    
    Args:
        company: Company instance
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional) 
        incremental: If True, only export data changed since last_backup_date
        last_backup_date: Date of last successful backup (for incremental)
    """
    from django.db.models import Q
    from django.utils import timezone
    
    # Set default end_date to now if not provided
    if end_date is None:
        end_date = timezone.now().date()
    
    # Create date filter conditions
    date_filter = Q()
    if start_date:
        date_filter &= Q(created_at__date__gte=start_date) | Q(updated_at__date__gte=start_date)
    if end_date:
        date_filter &= Q(created_at__date__lte=end_date) | Q(updated_at__date__lte=end_date)
    
    # Incremental filter
    incremental_filter = Q()
    if incremental and last_backup_date:
        incremental_filter = (
            Q(created_at__date__gt=last_backup_date) | 
            Q(updated_at__date__gt=last_backup_date)
        )
    
    # Create a temporary directory for the zip file
    backup_dir = os.path.join(settings.MEDIA_ROOT, 'temp_backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate filename with date range info
    date_suffix = ""
    if start_date or end_date:
        date_suffix = f"_from_{start_date or 'beginning'}_to_{end_date}"
    if incremental:
        date_suffix += "_incremental"
    
    zip_filename = f'backup_{company.name.lower().replace(" ", "_")}{date_suffix}_{timezone.now().strftime("%Y%m%d%H%M%S")}.zip'
    zip_filepath = os.path.join(backup_dir, zip_filename)

    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
        
        # 1. ACCOUNTS - Usually don't change often, include all unless incremental
        accounts = Account.objects.filter(company=company)
        if incremental and last_backup_date:
            accounts = accounts.filter(incremental_filter)
        
        if accounts.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'account_number', 'name', 'account_type', 'description', 'is_active', 'created_at', 'updated_at']
            writer.writerow(fields)
            
            for account in accounts:
                writer.writerow([
                    account.id, account.account_number, account.name,
                    account.account_type.name if account.account_type else '',
                    account.description, account.is_active, 
                    account.created_at, getattr(account, 'updated_at', account.created_at)
                ])
            zf.writestr('accounts.csv', output.getvalue())
        
        # 2. JOURNAL ENTRIES with date filtering
        journal_entries = JournalEntry.objects.filter(company=company)
        
        # Apply date range filter for journal entries
        if start_date:
            journal_entries = journal_entries.filter(date__gte=start_date)
        if end_date:
            journal_entries = journal_entries.filter(date__lte=end_date)
        
        # Apply incremental filter
        if incremental and last_backup_date:
            journal_entries = journal_entries.filter(incremental_filter)
        
        if journal_entries.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'date', 'description', 'created_by', 'created_at', 'updated_at']
            writer.writerow(fields)
            
            for entry in journal_entries:
                writer.writerow([
                    entry.id, entry.date, entry.description,
                    entry.created_by.username if entry.created_by else '',
                    entry.created_at, getattr(entry, 'updated_at', entry.created_at)
                ])
            zf.writestr('journal_entries.csv', output.getvalue())
        
        # 3. JOURNAL ENTRY LINES (related to filtered journal entries)
        journal_lines = JournalEntryLine.objects.filter(
            journal_entry__company=company,
            journal_entry__in=journal_entries
        )
        
        if journal_lines.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'journal_entry_id', 'journal_entry_date', 'account_name', 'account_number', 'debit', 'credit', 'description']
            writer.writerow(fields)
            
            for line in journal_lines:
                writer.writerow([
                    line.id, line.journal_entry.id, line.journal_entry.date,
                    line.account.name, line.account.account_number,
                    line.debit, line.credit, line.description
                ])
            zf.writestr('journal_entry_lines.csv', output.getvalue())
        
        # 4. TRANSACTIONS with date filtering
        transactions = Transaction.objects.filter(company=company)
        
        if start_date:
            transactions = transactions.filter(date__gte=start_date)
        if end_date:
            transactions = transactions.filter(date__lte=end_date)
        
        if incremental and last_backup_date:
            transactions = transactions.filter(incremental_filter)
        
        if transactions.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'transaction_type', 'date', 'due_date', 'customer_name', 'description', 
                     'total_amount', 'amount_paid', 'reference_number', 'created_at', 'updated_at']
            writer.writerow(fields)
            
            for txn in transactions:
                writer.writerow([
                    txn.id, txn.transaction_type, txn.date, txn.due_date,
                    txn.customer.name if txn.customer else '',
                    txn.description, txn.total_amount, txn.amount_paid,
                    txn.reference_number, txn.created_at, getattr(txn, 'updated_at', txn.created_at)
                ])
            zf.writestr('transactions.csv', output.getvalue())
        
        # 5. TRANSACTION ITEMS (related to filtered transactions)
        transaction_items = TransactionItem.objects.filter(transaction__in=transactions)
        if transaction_items.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'transaction_id', 'item_name', 'description', 'quantity', 'unit_price', 'line_total']
            writer.writerow(fields)
            
            for item in transaction_items:
                writer.writerow([
                    item.id, item.transaction.id, item.item.name,
                    item.description, item.quantity, item.unit_price, item.line_total
                ])
            zf.writestr('transaction_items.csv', output.getvalue())
        
        # 6. CUSTOMERS - Apply incremental filter only
        customers = Customer.objects.filter(company=company)
        if incremental and last_backup_date:
            customers = customers.filter(incremental_filter)
        
        if customers.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'name', 'entity_type', 'email', 'phone', 'address', 'credit_limit', 'created_at', 'updated_at']
            writer.writerow(fields)
            
            for customer in customers:
                writer.writerow([
                    customer.id, customer.name, customer.entity_type,
                    customer.email, customer.phone, customer.address,
                    customer.credit_limit, customer.created_at, getattr(customer, 'updated_at', customer.created_at)
                ])
            zf.writestr('customers.csv', output.getvalue())
        
        # 7. INVENTORY ITEMS - Apply incremental filter only
        inventory_items = InventoryItem.objects.filter(company=company)
        if incremental and last_backup_date:
            inventory_items = inventory_items.filter(incremental_filter)
        
        if inventory_items.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'name', 'sku', 'item_type', 'description', 'unit_of_measurement', 
                     'current_average_cost', 'sale_price', 'quantity_on_hand', 'reorder_level', 'costing_method']
            writer.writerow(fields)
            
            for item in inventory_items:
                writer.writerow([
                    item.id, item.name, item.sku, item.item_type,
                    item.description, item.unit_of_measurement,
                    item.current_average_cost, item.sale_price,
                    item.quantity_on_hand, item.reorder_level, item.costing_method
                ])
            zf.writestr('inventory_items.csv', output.getvalue())
        
        # 8. INVENTORY TRANSACTIONS with date filtering
        inventory_transactions = InventoryTransaction.objects.filter(company=company)
        
        if start_date:
            inventory_transactions = inventory_transactions.filter(transaction_date__date__gte=start_date)
        if end_date:
            inventory_transactions = inventory_transactions.filter(transaction_date__date__lte=end_date)
        
        if incremental and last_backup_date:
            inventory_transactions = inventory_transactions.filter(
                transaction_date__date__gt=last_backup_date
            )
        
        if inventory_transactions.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'item_name', 'transaction_type', 'quantity', 'unit_cost', 'total_cost', 'transaction_date', 'notes']
            writer.writerow(fields)
            
            for txn in inventory_transactions:
                writer.writerow([
                    txn.id, txn.item.name, txn.transaction_type,
                    txn.quantity, txn.unit_cost or 0, txn.total_cost or 0,
                    txn.transaction_date, txn.notes
                ])
            zf.writestr('inventory_transactions.csv', output.getvalue())
        
        # 9. INVENTORY COST LAYERS (related to filtered inventory items)
        from apps.inventory.models import InventoryCostLayer
        cost_layers = InventoryCostLayer.objects.filter(item__in=inventory_items)
        if cost_layers.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'item_name', 'purchase_date', 'quantity', 'quantity_remaining', 'unit_cost', 'reference']
            writer.writerow(fields)
            
            for layer in cost_layers:
                writer.writerow([
                    layer.id, layer.item.name, layer.purchase_date,
                    layer.quantity, layer.quantity_remaining, layer.unit_cost, layer.reference
                ])
            zf.writestr('inventory_cost_layers.csv', output.getvalue())
        
        # 10. ASSETS - Apply incremental filter only
        assets = Asset.objects.filter(company=company)
        if incremental and last_backup_date:
            assets = assets.filter(incremental_filter)
        
        if assets.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'name', 'description', 'purchase_date', 'purchase_price', 
                     'depreciation_method', 'useful_life_years', 'salvage_value']
            writer.writerow(fields)
            
            for asset in assets:
                writer.writerow([
                    asset.id, asset.name, asset.description,
                    asset.purchase_date, asset.purchase_price,
                    asset.depreciation_method, asset.useful_life_years, asset.salvage_value
                ])
            zf.writestr('assets.csv', output.getvalue())
        
        # 11. ASSET MAINTENANCE with date filtering
        maintenance_records = AssetMaintenance.objects.filter(asset__company=company)
        if start_date:
            maintenance_records = maintenance_records.filter(maintenance_date__gte=start_date)
        if end_date:
            maintenance_records = maintenance_records.filter(maintenance_date__lte=end_date)
        
        if maintenance_records.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'asset_name', 'maintenance_date', 'maintenance_type', 'description', 'cost']
            writer.writerow(fields)
            
            for record in maintenance_records:
                writer.writerow([
                    record.id, record.asset.name, record.maintenance_date,
                    record.maintenance_type, record.description, record.cost
                ])
            zf.writestr('asset_maintenance.csv', output.getvalue())
        
        # 12. DEPRECIATION ENTRIES with date filtering
        depreciation_entries = DepreciationEntry.objects.filter(asset__company=company)
        if start_date:
            depreciation_entries = depreciation_entries.filter(date__gte=start_date)
        if end_date:
            depreciation_entries = depreciation_entries.filter(date__lte=end_date)
        
        if depreciation_entries.exists():
            output = StringIO()
            writer = csv.writer(output)
            fields = ['id', 'asset_name', 'date', 'amount', 'journal_entry_id', 'created_at']
            writer.writerow(fields)
            
            for entry in depreciation_entries:
                writer.writerow([
                    entry.id, entry.asset.name, entry.date, entry.amount,
                    entry.journal_entry.id if entry.journal_entry else '',
                    entry.created_at
                ])
            zf.writestr('depreciation_entries.csv', output.getvalue())
        
        # 13. COMPANY INFORMATION
        output = StringIO()
        writer = csv.writer(output)
        fields = ['name', 'company_type', 'industry', 'registration_number', 'tax_number', 
                 'address', 'phone', 'email', 'website', 'currency', 'fiscal_year_start']
        writer.writerow(fields)
        writer.writerow([
            company.name, company.company_type, company.industry,
            company.registration_number, company.tax_number,
            company.address, company.phone, company.email,
            company.website, company.currency, company.fiscal_year_start
        ])
        zf.writestr('company_info.csv', output.getvalue())
        
        # Add metadata about the backup
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Backup Information', 'Value'])
        writer.writerow(['Company', company.name])
        writer.writerow(['Backup Type', 'Incremental' if incremental else 'Full'])
        writer.writerow(['Date Range Start', start_date or 'Beginning'])
        writer.writerow(['Date Range End', end_date])
        writer.writerow(['Last Backup Date', last_backup_date or 'N/A'])
        writer.writerow(['Generated At', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Total Files', len(zf.namelist())])
        zf.writestr('backup_info.csv', output.getvalue())
            
    return zip_filepath

def export_audit_documents_to_zip(company, start_date=None, end_date=None):
    """
    Creates a comprehensive audit package with all financial reports in multiple formats.
    Returns the path to the audit zip file.
    
    Args:
        company: Company instance
        start_date: Start date for audit period (optional)
        end_date: End date for audit period (optional)
    """
    from apps.reporting.export_utils import export_to_csv, export_to_excel, export_to_pdf
    from apps.accounts.models import AccountType
    from django.db.models import Sum, Q
    from datetime import date
    
    # Create audit directory
    audit_dir = os.path.join(settings.MEDIA_ROOT, 'temp_audits')
    os.makedirs(audit_dir, exist_ok=True)
    
    # Generate filename with date range info
    date_suffix = ""
    if start_date or end_date:
        date_suffix = f"_from_{start_date or 'beginning'}_to_{end_date or 'current'}"
    
    zip_filename = f'audit_package_{company.name.lower().replace(" ", "_")}{date_suffix}_{timezone.now().strftime("%Y%m%d%H%M%S")}.zip'
    zip_filepath = os.path.join(audit_dir, zip_filename)
    
    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
        
        # Create date filter for journal entries
        journal_date_filter = Q()
        if start_date:
            journal_date_filter &= Q(journal_entry__date__gte=start_date)
        if end_date:
            journal_date_filter &= Q(journal_entry__date__lte=end_date)
        
        # 1. TRIAL BALANCE (filtered by date range)
        accounts = Account.objects.filter(company=company).order_by('account_number')
        tb_data = []
        total_debits = 0
        total_credits = 0
        
        for account in accounts:
            # Calculate balance within date range if specified
            if start_date or end_date:
                lines = account.journal_lines.all()
                if start_date:
                    lines = lines.filter(journal_entry__date__gte=start_date)
                if end_date:
                    lines = lines.filter(journal_entry__date__lte=end_date)
                
                if not lines.exists():
                    continue
                    
                balance = lines.aggregate(
                    balance=Sum('debit', default=0) - Sum('credit', default=0)
                )['balance'] or 0
            else:
                balance = account.get_balance()
            
            if balance == 0:
                continue
                
            debit_balance = 0
            credit_balance = 0
            
            if account.account_type.category in [AccountType.Category.ASSET, AccountType.Category.EXPENSE]:
                if balance >= 0:
                    debit_balance = balance
                    total_debits += balance
                else:
                    credit_balance = abs(balance)
                    total_credits += abs(balance)
            else:
                if balance >= 0:
                    credit_balance = balance
                    total_credits += balance
                else:
                    debit_balance = abs(balance)
                    total_debits += abs(balance)
            
            tb_data.append([
                account.account_number,
                account.name,
                debit_balance if debit_balance > 0 else '',
                credit_balance if credit_balance > 0 else ''
            ])
        
        tb_data.append(['', 'TOTALS', total_debits, total_credits])
        tb_headers = ['Account Code', 'Account Name', 'Debit', 'Credit']
        
        # Save Trial Balance
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(tb_headers)
        writer.writerows(tb_data)
        zf.writestr('trial_balance.csv', output.getvalue())
        
        # 2. INCOME STATEMENT (filtered by date range)
        is_data = []
        is_data.append(['', '=== REVENUE ===', ''])
        
        # Filter revenue accounts by date range
        revenue_query = Account.objects.filter(
            company=company,
            account_type__category=AccountType.Category.REVENUE
        )
        
        if start_date or end_date:
            revenue_accounts = revenue_query.annotate(
                calculated_balance=Sum(
                    'journal_lines__credit',
                    filter=journal_date_filter,
                    default=0
                ) - Sum(
                    'journal_lines__debit',
                    filter=journal_date_filter,
                    default=0
                )
            ).exclude(calculated_balance=0)
        else:
            revenue_accounts = revenue_query.annotate(
                calculated_balance=Sum('journal_lines__credit', default=0) - Sum('journal_lines__debit', default=0)
            ).exclude(calculated_balance=0)
        
        total_revenue = 0
        for account in revenue_accounts:
            balance = account.calculated_balance
            total_revenue += balance
            is_data.append([account.account_number, account.name, balance])
        
        is_data.append(['', 'Total Revenue', total_revenue])
        is_data.append(['', '', ''])
        is_data.append(['', '=== EXPENSES ===', ''])
        
        # Filter expense accounts by date range
        expense_query = Account.objects.filter(
            company=company,
            account_type__category=AccountType.Category.EXPENSE
        )
        
        if start_date or end_date:
            expense_accounts = expense_query.annotate(
                calculated_balance=Sum(
                    'journal_lines__credit',
                    filter=journal_date_filter,
                    default=0
                ) - Sum(
                    'journal_lines__debit',
                    filter=journal_date_filter,
                    default=0
                )
            ).exclude(calculated_balance=0)
        else:
            expense_accounts = expense_query.annotate(
                calculated_balance=Sum('journal_lines__credit', default=0) - Sum('journal_lines__debit', default=0)
            ).exclude(calculated_balance=0)
        
        total_expenses = 0
        for account in expense_accounts:
            balance = account.calculated_balance * -1
            total_expenses += balance
            is_data.append([account.account_number, account.name, balance])
        
        is_data.append(['', 'Total Expenses', total_expenses])
        is_data.append(['', '', ''])
        
        net_income = total_revenue - total_expenses
        is_data.append(['', '=== NET INCOME ===', net_income])
        
        is_headers = ['Account Code', 'Account Name', 'Amount']
        
        # Save Income Statement CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(is_headers)
        writer.writerows(is_data)
        zf.writestr('income_statement.csv', output.getvalue())
        
        # 3. BALANCE SHEET (filtered by date range)
        bs_accounts = Account.objects.filter(company=company).exclude(
            account_type__category__in=[AccountType.Category.REVENUE, AccountType.Category.EXPENSE]
        ).order_by('account_number')
        
        # Calculate Retained Earnings with date filter
        if start_date or end_date:
            revenue_balance = Account.objects.filter(
                company=company, account_type__category=AccountType.Category.REVENUE
            ).aggregate(
                total=Sum(
                    'journal_lines__credit',
                    filter=journal_date_filter,
                    default=0
                ) - Sum(
                    'journal_lines__debit',
                    filter=journal_date_filter,
                    default=0
                )
            )['total'] or 0
            
            expense_balance = Account.objects.filter(
                company=company, account_type__category=AccountType.Category.EXPENSE
            ).aggregate(
                total=Sum(
                    'journal_lines__debit',
                    filter=journal_date_filter,
                    default=0
                ) - Sum(
                    'journal_lines__credit',
                    filter=journal_date_filter,
                    default=0
                )
            )['total'] or 0
        else:
            revenue_balance = Account.objects.filter(
                company=company, account_type__category=AccountType.Category.REVENUE
            ).aggregate(
                total=Sum('journal_lines__credit', default=0) - Sum('journal_lines__debit', default=0)
            )['total'] or 0
            
            expense_balance = Account.objects.filter(
                company=company, account_type__category=AccountType.Category.EXPENSE
            ).aggregate(
                total=Sum('journal_lines__debit', default=0) - Sum('journal_lines__credit', default=0)
            )['total'] or 0
        
        retained_earnings = revenue_balance - expense_balance
        
        bs_data = []
        bs_data.append(['', '=== ASSETS ===', ''])
        total_assets = 0
        
        for account in bs_accounts:
            if account.account_type.category == AccountType.Category.ASSET:
                if start_date or end_date:
                    lines = account.journal_lines.all()
                    if start_date:
                        lines = lines.filter(journal_entry__date__gte=start_date)
                    if end_date:
                        lines = lines.filter(journal_entry__date__lte=end_date)
                    
                    if lines.exists():
                        balance = lines.aggregate(
                            balance=Sum('debit', default=0) - Sum('credit', default=0)
                        )['balance'] or 0
                    else:
                        balance = 0
                else:
                    balance = account.get_balance()
                
                if balance != 0:
                    bs_data.append([account.account_number, account.name, abs(balance)])
                    total_assets += abs(balance)
        
        bs_data.append(['', 'Total Assets', total_assets])
        bs_data.append(['', '', ''])
        bs_data.append(['', '=== LIABILITIES ===', ''])
        
        total_liabilities = 0
        for account in bs_accounts:
            if account.account_type.category == AccountType.Category.LIABILITY:
                if start_date or end_date:
                    lines = account.journal_lines.all()
                    if start_date:
                        lines = lines.filter(journal_entry__date__gte=start_date)
                    if end_date:
                        lines = lines.filter(journal_entry__date__lte=end_date)
                    
                    if lines.exists():
                        balance = lines.aggregate(
                            balance=Sum('credit', default=0) - Sum('debit', default=0)
                        )['balance'] or 0
                    else:
                        balance = 0
                else:
                    balance = account.get_balance()
                
                if balance != 0:
                    bs_data.append([account.account_number, account.name, abs(balance)])
                    total_liabilities += abs(balance)
        
        bs_data.append(['', 'Total Liabilities', total_liabilities])
        bs_data.append(['', '', ''])
        bs_data.append(['', '=== EQUITY ===', ''])
        
        base_equity = 0
        for account in bs_accounts:
            if account.account_type.category == AccountType.Category.EQUITY:
                if start_date or end_date:
                    lines = account.journal_lines.all()
                    if start_date:
                        lines = lines.filter(journal_entry__date__gte=start_date)
                    if end_date:
                        lines = lines.filter(journal_entry__date__lte=end_date)
                    
                    if lines.exists():
                        balance = lines.aggregate(
                            balance=Sum('credit', default=0) - Sum('debit', default=0)
                        )['balance'] or 0
                    else:
                        balance = 0
                else:
                    balance = account.get_balance()
                
                if balance != 0:
                    bs_data.append([account.account_number, account.name, abs(balance)])
                    base_equity += abs(balance)
        
        bs_data.append(['', 'Retained Earnings', retained_earnings])
        total_equity = base_equity + retained_earnings
        bs_data.append(['', 'Total Equity', total_equity])
        bs_data.append(['', '', ''])
        bs_data.append(['', 'Total Liabilities & Equity', total_liabilities + total_equity])
        
        bs_headers = ['Account Code', 'Account Name', 'Amount']
        
        # Save Balance Sheet CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(bs_headers)
        writer.writerows(bs_data)
        zf.writestr('balance_sheet.csv', output.getvalue())
        
        # 4. GENERAL LEDGER (filtered by date range)
        gl_data = []
        gl_headers = ['Account Code', 'Account Name', 'Date', 'Description', 'Debit', 'Credit', 'Balance']
        
        accounts_with_transactions = Account.objects.filter(
            company=company, 
            journal_lines__isnull=False
        ).distinct().order_by('account_number')
        
        for account in accounts_with_transactions:
            lines = JournalEntryLine.objects.filter(account=account)
            
            # Apply date filtering
            if start_date:
                lines = lines.filter(journal_entry__date__gte=start_date)
            if end_date:
                lines = lines.filter(journal_entry__date__lte=end_date)
            
            lines = lines.order_by('journal_entry__date', 'id')
            
            if not lines.exists():
                continue
            
            running_balance = 0
            is_credit_balance_account = account.account_type.category in [
                AccountType.Category.LIABILITY, 
                AccountType.Category.EQUITY, 
                AccountType.Category.REVENUE
            ]
            
            # Add account header
            gl_data.append([f"{account.account_number} - {account.name}", '', '', '', '', '', ''])
            
            for line in lines:
                if is_credit_balance_account:
                    running_balance += (line.credit - line.debit)
                else:
                    running_balance += (line.debit - line.credit)
                
                gl_data.append([
                    '',
                    '',
                    line.journal_entry.date,
                    line.journal_entry.description,
                    line.debit if line.debit > 0 else '',
                    line.credit if line.credit > 0 else '',
                    running_balance
                ])
            
            gl_data.append(['', '', '', 'Final Balance:', '', '', running_balance])
            gl_data.append(['', '', '', '', '', '', ''])  # Spacer
        
        # Save General Ledger CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(gl_headers)
        writer.writerows(gl_data)
        zf.writestr('general_ledger.csv', output.getvalue())
        
        # 5. CUSTOMER/VENDOR LIST (no date filtering needed)
        customers = Customer.objects.filter(company=company)
        if customers.exists():
            customer_data = []
            customer_headers = ['Name', 'Type', 'Email', 'Phone', 'Address', 'Credit Limit', 'Receivable Balance', 'Payable Balance']
            
            for customer in customers:
                customer_data.append([
                    customer.name,
                    customer.get_entity_type_display(),
                    customer.email or '',
                    customer.phone or '',
                    customer.address or '',
                    customer.credit_limit,
                    customer.receivable_balance,
                    customer.payable_balance
                ])
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(customer_headers)
            writer.writerows(customer_data)
            zf.writestr('customers_vendors.csv', output.getvalue())
        
        # 6. INVENTORY LIST (updated to use current_average_cost)
        inventory_items = InventoryItem.objects.filter(company=company)
        if inventory_items.exists():
            inventory_data = []
            inventory_headers = ['Name', 'SKU', 'Type', 'Unit', 'Current Average Cost', 'Sale Price', 'Quantity on Hand', 'Reorder Level', 'Costing Method']
            
            for item in inventory_items:
                inventory_data.append([
                    item.name,
                    item.sku or '',
                    item.get_item_type_display(),
                    item.unit_of_measurement,
                    item.current_average_cost,
                    item.sale_price,
                    item.quantity_on_hand,
                    item.reorder_level,
                    item.get_costing_method_display()
                ])
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(inventory_headers)
            writer.writerows(inventory_data)
            zf.writestr('inventory_items.csv', output.getvalue())
        
        # 7. INVENTORY TRANSACTIONS (filtered by date range)
        inventory_transactions = InventoryTransaction.objects.filter(company=company)
        if start_date:
            inventory_transactions = inventory_transactions.filter(transaction_date__date__gte=start_date)
        if end_date:
            inventory_transactions = inventory_transactions.filter(transaction_date__date__lte=end_date)
        
        if inventory_transactions.exists():
            inv_txn_data = []
            inv_txn_headers = ['Date', 'Item', 'Transaction Type', 'Quantity', 'Unit Cost', 'Total Cost', 'Notes']
            
            for txn in inventory_transactions:
                inv_txn_data.append([
                    txn.transaction_date.date() if hasattr(txn.transaction_date, 'date') else txn.transaction_date,
                    txn.item.name,
                    txn.get_transaction_type_display(),
                    txn.quantity,
                    txn.unit_cost or 0,
                    txn.total_cost or 0,
                    txn.notes or ''
                ])
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(inv_txn_headers)
            writer.writerows(inv_txn_data)
            zf.writestr('inventory_transactions.csv', output.getvalue())
        
        # 8. ASSETS LIST (no date filtering needed)
        assets = Asset.objects.filter(company=company)
        if assets.exists():
            asset_data = []
            asset_headers = ['Name', 'Purchase Date', 'Purchase Price', 'Depreciation Method', 'Useful Life', 'Salvage Value', 'Current Book Value']
            
            for asset in assets:
                asset_data.append([
                    asset.name,
                    asset.purchase_date,
                    asset.purchase_price,
                    asset.get_depreciation_method_display(),
                    f"{asset.useful_life_years} years",
                    asset.salvage_value,
                    asset.current_book_value
                ])
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(asset_headers)
            writer.writerows(asset_data)
            zf.writestr('assets.csv', output.getvalue())
        
        # 9. TRANSACTIONS (filtered by date range)
        transactions = Transaction.objects.filter(company=company)
        if start_date:
            transactions = transactions.filter(date__gte=start_date)
        if end_date:
            transactions = transactions.filter(date__lte=end_date)
        
        if transactions.exists():
            txn_data = []
            txn_headers = ['Date', 'Type', 'Customer', 'Reference', 'Description', 'Total Amount', 'Amount Paid', 'Balance Due']
            
            for txn in transactions:
                balance_due = txn.total_amount - txn.amount_paid
                txn_data.append([
                    txn.date,
                    txn.get_transaction_type_display(),
                    txn.customer.name if txn.customer else '',
                    txn.reference_number or '',
                    txn.description,
                    txn.total_amount,
                    txn.amount_paid,
                    balance_due
                ])
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(txn_headers)
            writer.writerows(txn_data)
            zf.writestr('transactions.csv', output.getvalue())
        
        # 10. COMPANY INFORMATION
        company_data = []
        company_headers = ['Field', 'Value']
        company_info = [
            ['Company Name', company.name],
            ['Industry', company.industry or 'Not specified'],
            ['Registration Number', company.registration_number or 'Not provided'],
            ['Tax Number', company.tax_number or 'Not provided'],
            ['Address', company.address or 'Not provided'],
            ['Phone', company.phone or 'Not provided'],
            ['Email', company.email or 'Not provided'],
            ['Website', company.website or 'Not provided'],
            ['Currency', company.get_currency_display()],
            ['Fiscal Year Start', company.fiscal_year_start or 'Not set'],
            ['Report Generated', timezone.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(company_headers)
        writer.writerows(company_info)
        zf.writestr('company_information.csv', output.getvalue())
        
        # 11. AUDIT METADATA
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Audit Information', 'Value'])
        writer.writerow(['Company', company.name])
        writer.writerow(['Audit Period Start', start_date or 'Beginning of Records'])
        writer.writerow(['Audit Period End', end_date or 'Current Date'])
        writer.writerow(['Date Range Applied', 'Yes' if (start_date or end_date) else 'No'])
        writer.writerow(['Generated At', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Total Reports', len([name for name in zf.namelist() if name.endswith('.csv')])])
        zf.writestr('audit_info.csv', output.getvalue())
    
    return zip_filepath