# apps/reports/management/commands/diagnose_balance_sheet.py

from django.core.management.base import BaseCommand
from django.db.models import Sum, Q
from apps.accounts.models import Account, AccountType
from apps.journal.models import JournalEntryLine
from apps.core.models import Company
from decimal import Decimal

class Command(BaseCommand):
    help = 'Diagnose balance sheet calculation issues'

    def handle(self, *args, **options):
        companies = Company.objects.all()
        
        for company in companies:
            self.stdout.write(f"\n=== BALANCE SHEET DIAGNOSIS FOR {company.name} ===")
            
            # Get all accounts with balances
            accounts = Account.objects.filter(company=company)
            
            total_assets = Decimal('0.00')
            total_liabilities = Decimal('0.00')
            total_equity = Decimal('0.00')
            
            self.stdout.write(f"\n--- ACCOUNT HIERARCHY AND BALANCES ---")
            
            for account in accounts:
                balance = account.get_balance()
                if balance != 0:
                    account_type = account.account_type.category if account.account_type else "Unknown"
                    
                    # Show hierarchy
                    indent = "  " * account.level if hasattr(account, 'level') else ""
                    parent_info = f" (Parent: {account.parent.account_number})" if account.parent else " (Root)"
                    has_transactions = "✓" if account.journal_lines.exists() else "✗"
                    
                    self.stdout.write(f"{indent}{account.account_number} - {account.name}: ₦{balance} ({account_type}){parent_info} [Transactions: {has_transactions}]")
                    
                    # Only count LEAF accounts (accounts with actual transactions) for totals
                    if account.journal_lines.exists():
                        if account_type == AccountType.Category.ASSET:
                            total_assets += balance
                        elif account_type == AccountType.Category.LIABILITY:
                            total_liabilities += abs(balance)
                        elif account_type in [AccountType.Category.EQUITY, AccountType.Category.REVENUE]:
                            total_equity += abs(balance)
                        elif account_type == AccountType.Category.EXPENSE:
                            total_equity -= balance
            
            self.stdout.write(f"\n--- CORRECTED TOTALS (LEAF ACCOUNTS ONLY) ---")
            self.stdout.write(f"Total Assets: ₦{total_assets}")
            self.stdout.write(f"Total Liabilities: ₦{total_liabilities}")
            self.stdout.write(f"Total Equity: ₦{total_equity}")
            self.stdout.write(f"Assets - (Liabilities + Equity): ₦{total_assets - (total_liabilities + total_equity)}")
