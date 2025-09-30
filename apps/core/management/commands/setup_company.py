# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\management\commands\setup_company.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.core.models import Company
from apps.accounts.models import AccountType, Account
from apps.authentication.models import User

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up initial company and superuser for new installations'
    
    def add_arguments(self, parser):
        parser.add_argument('--company-name', required=True, help='Company name')
        parser.add_argument('--admin-username', required=True, help='Admin username')
        parser.add_argument('--admin-email', required=True, help='Admin email')
        parser.add_argument('--admin-password', required=True, help='Admin password')
        parser.add_argument('--currency', default='NGN', help='Company currency')
        parser.add_argument('--industry', default='General Business', help='Company industry')
    
    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Setting up new company...'))
        
        # 1. Create company
        company = Company.objects.create(
            name=options['company_name'],
            currency=options['currency'],
            industry=options['industry'],
            company_type=Company.CompanyType.USER
        )
        self.stdout.write(f"✅ Created company: {company.name}")
        
        # 2. Create auditor company with default data
        auditor_company = Company.objects.create(
            name="Wole Joshua & Co (Chartered Accountants)",
            phone="+2348030655969",
            email="omowolewa@gmail.com",
            address="Top Floor Apo Plaza, Opposite GTB Apo junction.",
            industry="Accounting and Auditing",
            company_type=Company.CompanyType.AUDITOR
        )
        self.stdout.write(f"✅ Created auditor company: {auditor_company.name}")
        
        # 3. Create superuser
        admin_user = User.objects.create_user(
            username=options['admin_username'],
            email=options['admin_email'],
            password=options['admin_password'],
            company=company,
            user_type=User.UserType.ADMIN,
            is_staff=True,
            is_superuser=True,
            force_password_change=False  # Don't force change for initial setup
        )
        self.stdout.write(f"✅ Created admin user: {admin_user.username}")
        
        # 4. Set up Chart of Accounts using existing command
        from apps.accounts.management.commands.seed_coa import Command as SeedCommand
        seed_command = SeedCommand()
        seed_command.handle(company_id=company.id)
        self.stdout.write("✅ Chart of Accounts created")
        
        # 5. Create comprehensive default transaction categories
        self.create_comprehensive_categories(company)
        
        # 6. Set up backup settings with defaults
        from apps.backup.models import BackupSettings
        BackupSettings.objects.create(
            company=company,
            backup_enabled=True,
            backup_frequency_days=7,
            debtor_reminders_enabled=True
        )
        self.stdout.write("✅ Default backup settings created")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Setup complete!\n'
                f'Company: {company.name}\n'
                f'Admin: {admin_user.username}\n'
                f'Login at: http://localhost:8000/auth/login/\n'
            )
        )
    
    def create_comprehensive_categories(self, company):
        """Create comprehensive default transaction categories for common business needs"""
        from apps.transactions.models import TransactionCategory
        from apps.accounts.models import AccountType
        
        try:
            # Get account types
            revenue_type = AccountType.objects.get(name='Revenue')
            expense_type = AccountType.objects.get(name='Expense')
            current_asset_type = AccountType.objects.get(name='Current Asset')
            current_liability_type = AccountType.objects.get(name='Current Liability')
            
            # Get specific accounts for linking
            sales_revenue_account = Account.objects.filter(
                company=company, account_number='4100'
            ).first()
            
            office_rent_account = Account.objects.filter(
                company=company, account_number='6100'
            ).first()
            
            staff_salaries_account = Account.objects.filter(
                company=company, account_number='6200'
            ).first()
            
            office_supplies_account = Account.objects.filter(
                company=company, account_number='6300'
            ).first()
            
            utilities_account = Account.objects.filter(
                company=company, account_number='6400'
            ).first()
            
            # Comprehensive transaction categories
            categories = [
                # 🎯 REVENUE CATEGORIES
                {
                    'name': 'Product Sales',
                    'account_type': revenue_type,
                    'default_account': sales_revenue_account,
                    'allowed_transaction_types': ['SALE'],
                    'description': 'Revenue from selling physical products'
                },
                {
                    'name': 'Service Revenue',
                    'account_type': revenue_type,
                    'default_account': sales_revenue_account,
                    'allowed_transaction_types': ['SALE'],
                    'description': 'Revenue from providing services'
                },
                {
                    'name': 'Consulting Fees',
                    'account_type': revenue_type,
                    'default_account': sales_revenue_account,
                    'allowed_transaction_types': ['SALE'],
                    'description': 'Revenue from consulting and advisory services'
                },
                {
                    'name': 'Interest Income',
                    'account_type': revenue_type,
                    'allowed_transaction_types': ['SALE', 'ADJUSTMENT'],
                    'description': 'Interest earned on bank deposits and investments'
                },
                
                # 🎯 OPERATING EXPENSE CATEGORIES
                {
                    'name': 'Office Rent',
                    'account_type': expense_type,
                    'default_account': office_rent_account,
                    'allowed_transaction_types': ['EXPENSE', 'PURCHASE'],
                    'description': 'Monthly office rent and lease payments'
                },
                {
                    'name': 'Staff Salaries',
                    'account_type': expense_type,
                    'default_account': staff_salaries_account,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Employee salaries and wages'
                },
                {
                    'name': 'Office Supplies',
                    'account_type': expense_type,
                    'default_account': office_supplies_account,
                    'allowed_transaction_types': ['EXPENSE', 'PURCHASE'],
                    'description': 'Stationery, printing materials, and office consumables'
                },
                {
                    'name': 'Utilities',
                    'account_type': expense_type,
                    'default_account': utilities_account,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Electricity, water, internet, and phone bills'
                },
                {
                    'name': 'Transportation',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Business travel, fuel, and transportation costs'
                },
                {
                    'name': 'Marketing & Advertising',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE', 'PURCHASE'],
                    'description': 'Promotional activities, advertising, and marketing campaigns'
                },
                {
                    'name': 'Professional Services',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE', 'PURCHASE'],
                    'description': 'Legal fees, accounting services, consultancy'
                },
                {
                    'name': 'Insurance',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Business insurance premiums'
                },
                {
                    'name': 'Bank Charges',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Bank fees, transaction charges, and service fees'
                },
                {
                    'name': 'Training & Development',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Staff training, courses, and professional development'
                },
                {
                    'name': 'Equipment Maintenance',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Repair and maintenance of office equipment'
                },
                {
                    'name': 'Software & Subscriptions',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Software licenses, SaaS subscriptions, and digital tools'
                },
                
                # 🎯 INVENTORY & PURCHASING CATEGORIES
                {
                    'name': 'Inventory Purchase',
                    'account_type': current_asset_type,
                    'allowed_transaction_types': ['PURCHASE'],
                    'description': 'Purchase of goods for resale'
                },
                {
                    'name': 'Raw Materials',
                    'account_type': current_asset_type,
                    'allowed_transaction_types': ['PURCHASE'],
                    'description': 'Raw materials for manufacturing'
                },
                {
                    'name': 'Equipment Purchase',
                    'account_type': current_asset_type,
                    'allowed_transaction_types': ['PURCHASE'],
                    'description': 'Purchase of office equipment and machinery'
                },
                
                # 🎯 FINANCIAL CATEGORIES
                {
                    'name': 'Loan Repayment',
                    'account_type': current_liability_type,
                    'allowed_transaction_types': ['PAYMENT', 'EXPENSE'],
                    'description': 'Loan principal and interest payments'
                },
                {
                    'name': 'Tax Payments',
                    'account_type': current_liability_type,
                    'allowed_transaction_types': ['PAYMENT', 'EXPENSE'],
                    'description': 'Income tax, VAT, and other tax payments'
                },
                {
                    'name': 'Owner Drawings',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE', 'PAYMENT'],
                    'description': 'Money withdrawn by business owner for personal use'
                },
                
                # 🎯 MISCELLANEOUS CATEGORIES
                {
                    'name': 'Petty Cash Expenses',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Small miscellaneous expenses paid from petty cash'
                },
                {
                    'name': 'Entertainment',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Business entertainment and client hospitality'
                },
                {
                    'name': 'Donations & Charity',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Charitable donations and community contributions'
                },
                {
                    'name': 'Research & Development',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE', 'PURCHASE'],
                    'description': 'R&D activities and innovation expenses'
                },
                
                # 🎯 INDUSTRY-SPECIFIC CATEGORIES (can be customized)
                {
                    'name': 'Freight & Shipping',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Shipping costs and freight charges'
                },
                {
                    'name': 'Quality Control',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Quality assurance and testing expenses'
                },
                {
                    'name': 'Licensing & Permits',
                    'account_type': expense_type,
                    'allowed_transaction_types': ['EXPENSE'],
                    'description': 'Business licenses, permits, and regulatory fees'
                },
            ]
            
            # Create categories
            created_count = 0
            for cat_data in categories:
                try:
                    category = TransactionCategory.objects.create(
                        company=company,
                        **cat_data
                    )
                    created_count += 1
                    self.stdout.write(f"  ✓ Created category: {category.name}")
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Failed to create category '{cat_data['name']}': {e}")
                    )
            
            self.stdout.write(f"✅ Created {created_count} default transaction categories")
            
            # Create a helpful summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n📊 Transaction Categories Summary:\n"
                    f"   • Revenue Categories: 4\n"
                    f"   • Operating Expense Categories: 12\n"
                    f"   • Inventory & Purchasing Categories: 3\n"
                    f"   • Financial Categories: 3\n"
                    f"   • Miscellaneous Categories: 4\n"
                    f"   • Industry-Specific Categories: 3\n"
                    f"   📝 Users can add more categories as needed through the admin panel.\n"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error creating transaction categories: {e}")
            )
