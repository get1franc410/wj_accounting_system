# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\accounts\management\commands\seed_coa.py

import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import Account, AccountType
from apps.core.models import Company
from apps.journal.models import JournalEntry, JournalEntryLine
from apps.inventory.models import InventoryItem, InventoryTransaction
from apps.assets.models import Asset, AssetMaintenance, DepreciationEntry
from apps.transactions.models import TransactionCategory, Transaction, TransactionItem
from apps.customers.models import Customer

CHART_OF_ACCOUNTS = {
    'Current Asset': [
        {'number': '1110', 'name': 'Bank Accounts', 'parent': None, 'system_account': Account.SystemAccount.DEFAULT_CASH},
        {'number': '1200', 'name': 'Accounts Receivable', 'parent': None, 'is_control': True, 'system_account': Account.SystemAccount.ACCOUNTS_RECEIVABLE},
        {'number': '1300', 'name': 'Inventory Asset', 'parent': None, 'system_account': Account.SystemAccount.INVENTORY_ASSET},
    ],
    'Fixed Asset': [
        {'number': '1500', 'name': 'Fixed Assets', 'parent': None},
        {'number': '1510', 'name': 'Land', 'parent': '1500'},
        {'number': '1520', 'name': 'Buildings', 'parent': '1500'},
        {'number': '1530', 'name': 'Machinery & Equipment', 'parent': '1500'},
        {'number': '1540', 'name': 'Vehicles', 'parent': '1500'},
        {'number': '1550', 'name': 'Office Equipment', 'parent': '1500'},  # ✅ ADDED
    ],
    'Accumulated Depreciation': [
        {'number': '1600', 'name': 'Accumulated Depreciation', 'parent': None},
        {'number': '1620', 'name': 'Accumulated Depreciation - Buildings', 'parent': '1600'},
        {'number': '1630', 'name': 'Accumulated Depreciation - Machinery', 'parent': '1600'},
        {'number': '1640', 'name': 'Accumulated Depreciation - Vehicles', 'parent': '1600'},
        {'number': '1650', 'name': 'Accumulated Depreciation - Office Equipment', 'parent': '1600'},  # ✅ ADDED
    ],
    'Current Liability': [
        {'number': '2100', 'name': 'Current Liabilities', 'parent': None},
        {'number': '2200', 'name': 'Accounts Payable', 'parent': '2100', 'is_control': True, 'system_account': Account.SystemAccount.ACCOUNTS_PAYABLE},
        {'number': '2300', 'name': 'Sales Tax Payable', 'parent': '2100', 'system_account': Account.SystemAccount.SALES_TAX_PAYABLE},
    ],
    'Equity': [
        {'number': '3000', 'name': 'Equity', 'parent': None},
        {'number': '3100', 'name': 'Owner\'s Capital', 'parent': '3000'},
        {'number': '3200', 'name': 'Retained Earnings', 'parent': '3000', 'system_account': Account.SystemAccount.RETAINED_EARNINGS},
    ],
    'Revenue': [
        {'number': '4000', 'name': 'Income / Revenue', 'parent': None},
        {'number': '4100', 'name': 'Sales Revenue', 'parent': '4000'},
        {'number': '4200', 'name': 'Service Revenue', 'parent': '4000'},
        {'number': '4300', 'name': 'Interest Income', 'parent': '4000'},
    ],
    'Expense': [
        {'number': '5000', 'name': 'Expenses', 'parent': None},
        {'number': '5100', 'name': 'Cost of Goods Sold', 'parent': '5000', 'system_account': Account.SystemAccount.COST_OF_GOODS_SOLD},
        {'number': '5200', 'name': 'Rent Expense', 'parent': '5000'},
        {'number': '5300', 'name': 'Salaries & Wages', 'parent': '5000'},
        {'number': '5400', 'name': 'Office Supplies', 'parent': '5000'},
        {'number': '6100', 'name': 'Office Rent', 'parent': '5000'},  # ✅ ADDED
        {'number': '6200', 'name': 'Staff Salaries', 'parent': '5000'},  # ✅ ADDED
        {'number': '6300', 'name': 'Office Supplies Expense', 'parent': '5000'},  # ✅ ADDED
        {'number': '6400', 'name': 'Utilities Expense', 'parent': '5000'},  # ✅ ADDED
    ],
    'Depreciation Expense': [
        {'number': '5500', 'name': 'Depreciation Expense', 'parent': None},
        {'number': '5520', 'name': 'Depreciation - Buildings', 'parent': '5500'},
        {'number': '5530', 'name': 'Depreciation - Machinery', 'parent': '5500'},
        {'number': '5540', 'name': 'Depreciation - Vehicles', 'parent': '5500'},
        {'number': '7020', 'name': 'Depreciation - Buildings Alt', 'parent': '5500'},  # ✅ ADDED
        {'number': '7030', 'name': 'Depreciation - Machinery Alt', 'parent': '5500'},  # ✅ ADDED
        {'number': '7040', 'name': 'Depreciation - Vehicles Alt', 'parent': '5500'},  # ✅ ADDED
        {'number': '7050', 'name': 'Depreciation - Office Equipment', 'parent': '5500'},  # ✅ ADDED
    ]
}

class Command(BaseCommand):
    help = 'Seeds the database with a standard Chart of Accounts for a specific company.'

    def add_arguments(self, parser):
        parser.add_argument('company_id', type=int, help='The ID of the company to seed the CoA for.')

    @transaction.atomic
    def handle(self, *args, **kwargs):
        company_id = kwargs['company_id']
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Company with ID "{company_id}" does not exist.'))
            sys.exit(1)

        self.stdout.write(self.style.WARNING(f'Starting data cleanup for {company.name}...'))

        # ✅ FIXED: Delete dependent objects in the CORRECT ORDER to avoid ProtectedError
        self.stdout.write('  - Clearing dependent data in proper order...')
        
        # Step 1: Delete most dependent objects first
        self.stdout.write('    - Clearing journal entry lines...')
        JournalEntryLine.objects.filter(journal_entry__company=company).delete()
        
        self.stdout.write('    - Clearing journal entries...')
        JournalEntry.objects.filter(company=company).delete()
        
        self.stdout.write('    - Clearing transaction items...')
        TransactionItem.objects.filter(transaction__company=company).delete()
        
        self.stdout.write('    - Clearing transactions...')
        Transaction.objects.filter(company=company).delete()
        
        self.stdout.write('    - Clearing transaction categories...')
        TransactionCategory.objects.filter(company=company).delete()
        
        self.stdout.write('    - Clearing inventory transactions...')
        InventoryTransaction.objects.filter(company=company).delete()
        
        self.stdout.write('    - Clearing inventory items...')
        InventoryItem.objects.filter(company=company).delete()
        
        self.stdout.write('    - Clearing asset maintenance records...')
        AssetMaintenance.objects.filter(asset__company=company).delete()
        
        self.stdout.write('    - Clearing depreciation entries...')
        DepreciationEntry.objects.filter(asset__company=company).delete()
        
        self.stdout.write('    - Clearing assets...')
        Asset.objects.filter(company=company).delete()
        
        self.stdout.write('    - Clearing customers...')
        Customer.objects.filter(company=company).delete()

        # Step 2: Now it's safe to delete the accounts
        self.stdout.write('  - Clearing Chart of Accounts...')
        Account.objects.filter(company=company).delete()
        
        self.stdout.write(self.style.SUCCESS('Data cleanup complete. Seeding new Chart of Accounts...'))
        
        account_type_definitions = {
            'Current Asset': {'category': AccountType.Category.ASSET, 'name': 'Current Asset'},
            'Fixed Asset': {'category': AccountType.Category.ASSET, 'name': 'Fixed Asset'},
            'Accumulated Depreciation': {'category': AccountType.Category.ASSET, 'name': 'Accumulated Depreciation'},
            'Current Liability': {'category': AccountType.Category.LIABILITY, 'name': 'Current Liability'},
            'Equity': {'category': AccountType.Category.EQUITY, 'name': 'Equity'},
            'Revenue': {'category': AccountType.Category.REVENUE, 'name': 'Revenue'},
            'Expense': {'category': AccountType.Category.EXPENSE, 'name': 'Expense'},
            'Depreciation Expense': {'category': AccountType.Category.EXPENSE, 'name': 'Depreciation Expense'},
        }

        account_types = {}
        self.stdout.write('  - Seeding Account Types with categories...')
        for key, definition in account_type_definitions.items():
            acc_type, created = AccountType.objects.update_or_create(
                name=definition['name'],
                defaults={'category': definition['category']}
            )
            account_types[key] = acc_type
            if created:
                self.stdout.write(f'    - Created AccountType: {definition["name"]}')
            else:
                self.stdout.write(f'    - Updated AccountType: {definition["name"]}')

        created_accounts = {}
        self.stdout.write('  - Creating accounts...')
        for type_name, accounts_list in CHART_OF_ACCOUNTS.items():
            account_type = account_types[type_name]
            for acc_data in accounts_list:
                parent_acc = created_accounts.get(acc_data['parent']) if acc_data['parent'] else None
                
                account = Account.objects.create(
                    company=company,
                    account_type=account_type,
                    name=acc_data['name'],
                    account_number=acc_data['number'],
                    parent=parent_acc,
                    is_control_account=acc_data.get('is_control', False),
                    system_account=acc_data.get('system_account', None)
                )
                created_accounts[acc_data['number']] = account
                self.stdout.write(f'    - Created: {acc_data["number"]} - {acc_data["name"]}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded Chart of Accounts for {company.name}.'))
        self.stdout.write(f'Total accounts created: {len(created_accounts)}')
