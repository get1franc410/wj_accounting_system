# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\transactions\management\commands\create_default_categories.py

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Company
from apps.accounts.models import Account, AccountType
from apps.transactions.models import TransactionCategory
from apps.transactions.constants import TransactionType

class Command(BaseCommand):
    help = 'Creates comprehensive default transaction categories for a company'
    
    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, help='Specific company ID to create categories for')
        parser.add_argument('--overwrite', action='store_true', help='Overwrite existing categories')
        parser.add_argument('--preview', action='store_true', help='Preview categories without creating them')
    
    @transaction.atomic
    def handle(self, *args, **options):
        company_id = options.get('company_id')
        overwrite = options.get('overwrite', False)
        preview = options.get('preview', False)
        
        if preview:
            self.stdout.write(self.style.WARNING('PREVIEW MODE - No categories will be created'))
        
        # Get companies to process
        if company_id:
            companies = Company.objects.filter(
                id=company_id, 
                company_type=Company.CompanyType.USER,
                is_active=True
            )
        else:
            companies = Company.objects.filter(
                company_type=Company.CompanyType.USER,
                is_active=True
            )
        
        if not companies.exists():
            self.stdout.write(self.style.ERROR("No active user companies found."))
            return
        
        for company in companies:
            self.stdout.write(f"\n🏢 Processing company: {company.name}")
            
            # Check if company has accounts
            if not company.accounts.exists():
                self.stdout.write(self.style.WARNING(f"  ⚠️ No accounts found for {company.name}. Run seed_coa first."))
                continue
            
            # Clear existing categories if overwrite is True
            if overwrite and not preview:
                existing_count = TransactionCategory.objects.filter(company=company).count()
                if existing_count > 0:
                    TransactionCategory.objects.filter(company=company).delete()
                    self.stdout.write(f"  🗑️ Removed {existing_count} existing categories")
            
            # Create categories
            created_categories = self.create_comprehensive_categories(company, preview)
            
            if preview:
                self.stdout.write(f"  📋 Would create {len(created_categories)} categories")
            else:
                self.stdout.write(f"  ✅ Created {len(created_categories)} transaction categories")
    
    def create_comprehensive_categories(self, company, preview=False):
        """Create comprehensive transaction categories based on chart of accounts"""
        
        # Get account types
        try:
            revenue_type = AccountType.objects.get(name='Revenue')
            expense_type = AccountType.objects.get(name='Expense') 
            depreciation_expense_type = AccountType.objects.get(name='Depreciation Expense')
            current_asset_type = AccountType.objects.get(name='Current Asset')
            fixed_asset_type = AccountType.objects.get(name='Fixed Asset')
            current_liability_type = AccountType.objects.get(name='Current Liability')
            equity_type = AccountType.objects.get(name='Equity')
        except AccountType.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Required account type not found: {e}"))
            return []
        
        # Comprehensive category definitions
        categories_data = [
            # 🎯 REVENUE CATEGORIES (Sales & Income)
            {
                'name': 'Product Sales',
                'account_type': revenue_type,
                'allowed_transaction_types': [TransactionType.SALE],
                'account_numbers': ['4100', '4000'],
                'description': 'Revenue from selling physical products and goods',
                'priority': 1
            },
            {
                'name': 'Service Revenue',
                'account_type': revenue_type,
                'allowed_transaction_types': [TransactionType.SALE],
                'account_numbers': ['4200', '4000'],
                'description': 'Revenue from providing services and consultancy',
                'priority': 1
            },
            {
                'name': 'Consulting Fees',
                'account_type': revenue_type,
                'allowed_transaction_types': [TransactionType.SALE],
                'account_numbers': ['4200', '4000'],
                'description': 'Revenue from consulting and advisory services',
                'priority': 2
            },
            {
                'name': 'Interest Income',
                'account_type': revenue_type,
                'allowed_transaction_types': [TransactionType.SALE, TransactionType.ADJUSTMENT],
                'account_numbers': ['4300', '4000'],
                'description': 'Interest earned on bank deposits and investments',
                'priority': 2
            },
            {
                'name': 'Other Income',
                'account_type': revenue_type,
                'allowed_transaction_types': [TransactionType.SALE, TransactionType.ADJUSTMENT],
                'account_numbers': ['4300', '4000'],
                'description': 'Miscellaneous income and other revenue sources',
                'priority': 3
            },
            
            # 🎯 OPERATING EXPENSE CATEGORIES
            {
                'name': 'Office Rent',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE, TransactionType.PURCHASE],
                'account_numbers': ['6100', '5200', '5000'],
                'description': 'Monthly office rent and lease payments',
                'priority': 1
            },
            {
                'name': 'Staff Salaries & Wages',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['6200', '5300', '5000'],
                'description': 'Employee salaries, wages, and compensation',
                'priority': 1
            },
            {
                'name': 'Office Supplies',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE, TransactionType.PURCHASE],
                'account_numbers': ['6300', '5400', '5000'],
                'description': 'Stationery, printing materials, and office consumables',
                'priority': 1
            },
            {
                'name': 'Utilities & Communications',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['6400', '5000'],
                'description': 'Electricity, water, internet, phone, and utility bills',
                'priority': 1
            },
            {
                'name': 'Transportation & Travel',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Business travel, fuel, transportation, and vehicle expenses',
                'priority': 2
            },
            {
                'name': 'Marketing & Advertising',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE, TransactionType.PURCHASE],
                'account_numbers': ['5000'],
                'description': 'Promotional activities, advertising, and marketing campaigns',
                'priority': 2
            },
            {
                'name': 'Professional Services',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE, TransactionType.PURCHASE],
                'account_numbers': ['5000'],
                'description': 'Legal fees, accounting services, consultancy, and professional fees',
                'priority': 2
            },
            {
                'name': 'Insurance Premiums',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Business insurance premiums and coverage costs',
                'priority': 2
            },
            {
                'name': 'Bank Charges & Fees',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Bank fees, transaction charges, and financial service fees',
                'priority': 2
            },
            {
                'name': 'Training & Development',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Staff training, courses, and professional development',
                'priority': 3
            },
            {
                'name': 'Equipment Maintenance & Repairs',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Repair and maintenance of office equipment and machinery',
                'priority': 2
            },
            {
                'name': 'Software & Subscriptions',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Software licenses, SaaS subscriptions, and digital tools',
                'priority': 2
            },
            {
                'name': 'Cost of Goods Sold',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.SALE, TransactionType.ADJUSTMENT],
                'account_numbers': ['5100', '5000'],
                'description': 'Direct costs of goods sold to customers',
                'priority': 1
            },
            
            # 🎯 INVENTORY & PURCHASING CATEGORIES
            {
                'name': 'Inventory Purchase',
                'account_type': current_asset_type,
                'allowed_transaction_types': [TransactionType.PURCHASE],
                'account_numbers': ['1300', '1110'],
                'description': 'Purchase of goods for resale and inventory',
                'priority': 1
            },
            {
                'name': 'Raw Materials Purchase',
                'account_type': current_asset_type,
                'allowed_transaction_types': [TransactionType.PURCHASE],
                'account_numbers': ['1300', '1110'],
                'description': 'Raw materials for manufacturing and production',
                'priority': 2
            },
            {
                'name': 'Equipment Purchase',
                'account_type': fixed_asset_type,
                'allowed_transaction_types': [TransactionType.PURCHASE],
                'account_numbers': ['1550', '1530', '1500'],
                'description': 'Purchase of office equipment, machinery, and fixed assets',
                'priority': 2
            },
            {
                'name': 'Vehicle Purchase',
                'account_type': fixed_asset_type,
                'allowed_transaction_types': [TransactionType.PURCHASE],
                'account_numbers': ['1540', '1500'],
                'description': 'Purchase of company vehicles and transportation equipment',
                'priority': 3
            },
            
            # 🎯 FINANCIAL & LIABILITY CATEGORIES
            {
                'name': 'Loan Payments',
                'account_type': current_liability_type,
                'allowed_transaction_types': [TransactionType.PAYMENT, TransactionType.EXPENSE],
                'account_numbers': ['2100'],
                'description': 'Loan principal and interest payments',
                'priority': 2
            },
            {
                'name': 'Tax Payments',
                'account_type': current_liability_type,
                'allowed_transaction_types': [TransactionType.PAYMENT, TransactionType.EXPENSE],
                'account_numbers': ['2300', '2100'],
                'description': 'Income tax, VAT, sales tax, and other tax payments',
                'priority': 2
            },
            {
                'name': 'Vendor Payments',
                'account_type': current_liability_type,
                'allowed_transaction_types': [TransactionType.PAYMENT],
                'account_numbers': ['2200', '2100'],
                'description': 'Payments to suppliers and vendors for purchases',
                'priority': 1
            },
            {
                'name': 'Owner Drawings',
                'account_type': equity_type,
                'allowed_transaction_types': [TransactionType.EXPENSE, TransactionType.PAYMENT],
                'account_numbers': ['3100', '3000'],
                'description': 'Money withdrawn by business owner for personal use',
                'priority': 2
            },
            {
                'name': 'Capital Contributions',
                'account_type': equity_type,
                'allowed_transaction_types': [TransactionType.SALE, TransactionType.ADJUSTMENT],
                'account_numbers': ['3100', '3000'],
                'description': 'Owner capital contributions and investments',
                'priority': 3
            },
            
            # 🎯 DEPRECIATION CATEGORIES
            {
                'name': 'Building Depreciation',
                'account_type': depreciation_expense_type,
                'allowed_transaction_types': [TransactionType.ADJUSTMENT],
                'account_numbers': ['5520', '7020', '5500'],
                'description': 'Depreciation expense for buildings and structures',
                'priority': 3
            },
            {
                'name': 'Equipment Depreciation',
                'account_type': depreciation_expense_type,
                'allowed_transaction_types': [TransactionType.ADJUSTMENT],
                'account_numbers': ['7050', '5530', '5500'],
                'description': 'Depreciation expense for equipment and machinery',
                'priority': 3
            },
            {
                'name': 'Vehicle Depreciation',
                'account_type': depreciation_expense_type,
                'allowed_transaction_types': [TransactionType.ADJUSTMENT],
                'account_numbers': ['5540', '7040', '5500'],
                'description': 'Depreciation expense for vehicles and transportation',
                'priority': 3
            },
            
            # 🎯 MISCELLANEOUS CATEGORIES
            {
                'name': 'Petty Cash Expenses',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Small miscellaneous expenses paid from petty cash',
                'priority': 2
            },
            {
                'name': 'Entertainment & Hospitality',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Business entertainment, client hospitality, and meals',
                'priority': 3
            },
            {
                'name': 'Donations & Charity',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Charitable donations and community contributions',
                'priority': 3
            },
            {
                'name': 'Research & Development',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE, TransactionType.PURCHASE],
                'account_numbers': ['5000'],
                'description': 'R&D activities, innovation, and product development expenses',
                'priority': 3
            },
            {
                'name': 'Freight & Shipping',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Shipping costs, freight charges, and delivery expenses',
                'priority': 2
            },
            {
                'name': 'Quality Control & Testing',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Quality assurance, testing, and compliance expenses',
                'priority': 3
            },
            {
                'name': 'Licensing & Permits',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Business licenses, permits, and regulatory fees',
                'priority': 2
            },
            {
                'name': 'Security Services',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Security services, surveillance, and safety expenses',
                'priority': 3
            },
            {
                'name': 'Cleaning & Maintenance',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.EXPENSE],
                'account_numbers': ['5000'],
                'description': 'Cleaning services, janitorial, and facility maintenance',
                'priority': 2
            },
            {
                'name': 'Bad Debt Expense',
                'account_type': expense_type,
                'allowed_transaction_types': [TransactionType.ADJUSTMENT],
                'account_numbers': ['5000'],
                'description': 'Write-off of uncollectible customer debts',
                'priority': 3
            },
        ]
        
        # Sort by priority (lower number = higher priority)
        categories_data.sort(key=lambda x: x['priority'])
        
        created_categories = []
        
        for cat_data in categories_data:
            try:
                # Find the best matching account
                default_account = self.find_best_account(company, cat_data['account_numbers'])
                
                if not default_account:
                    if not preview:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠️ No suitable account found for '{cat_data['name']}' "
                                f"(tried: {', '.join(cat_data['account_numbers'])})"
                            )
                        )
                    continue
                
                if preview:
                    self.stdout.write(
                        f"  📋 Would create: {cat_data['name']} -> "
                        f"{default_account.account_number} ({default_account.name})"
                    )
                    created_categories.append(cat_data['name'])
                    continue
                
                # Check if category already exists
                if TransactionCategory.objects.filter(company=company, name=cat_data['name']).exists():
                    self.stdout.write(f"  ⏭️ Category '{cat_data['name']}' already exists, skipping")
                    continue
                
                # Create the category
                category = TransactionCategory.objects.create(
                    company=company,
                    name=cat_data['name'],
                    account_type=cat_data['account_type'],
                    allowed_transaction_types=cat_data['allowed_transaction_types'],
                    default_account=default_account,
                    description=cat_data['description']
                )
                
                created_categories.append(category)
                
                priority_icon = "🔥" if cat_data['priority'] == 1 else "⭐" if cat_data['priority'] == 2 else "💡"
                self.stdout.write(
                    f"  {priority_icon} Created: {cat_data['name']} -> "
                    f"{default_account.account_number} ({default_account.name})"
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Failed to create category '{cat_data['name']}': {str(e)}")
                )
        
        return created_categories
    
    def find_best_account(self, company, account_numbers):
        """Find the best matching account from a list of account numbers"""
        for acc_number in account_numbers:
            # Try exact match first
            account = company.accounts.filter(account_number=acc_number).first()
            if account:
                return account
            
            # Try prefix match (e.g., '5000' matches '5000', '5100', etc.)
            account = company.accounts.filter(account_number__startswith=acc_number).first()
            if account:
                return account
        
        return None
