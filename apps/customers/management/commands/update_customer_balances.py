# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\customers\management\commands\update_customer_balances.py

from django.core.management.base import BaseCommand
from apps.customers.models import Customer
from decimal import Decimal

class Command(BaseCommand):
    help = 'Update all customer balances from transactions'
    
    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, help='Update balances for specific company')
    
    def handle(self, *args, **options):
        if options['company_id']:
            customers = Customer.objects.filter(company_id=options['company_id'])
            self.stdout.write(f'Updating balances for company ID: {options["company_id"]}')
        else:
            customers = Customer.objects.all()
            self.stdout.write('Updating balances for all customers')
        
        total_customers = customers.count()
        self.stdout.write(f'Found {total_customers} customers to process...')
        
        updated_count = 0
        unchanged_count = 0
        
        for customer in customers:
            # Store old balances
            old_receivable = customer.receivable_balance
            old_payable = customer.payable_balance
            
            # Update balances (your existing method doesn't return values)
            customer.update_balances()
            
            # Refresh from database to get updated values
            customer.refresh_from_db()
            
            # Check if balances changed
            if (old_receivable != customer.receivable_balance or 
                old_payable != customer.payable_balance):
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Updated {customer.name}: "
                        f"Receivable: {old_receivable} → {customer.receivable_balance}, "
                        f"Payable: {old_payable} → {customer.payable_balance}"
                    )
                )
            else:
                unchanged_count += 1
                self.stdout.write(
                    f"- {customer.name}: No changes needed "
                    f"(R: {customer.receivable_balance}, P: {customer.payable_balance})"
                )
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS(f'SUMMARY:'))
        self.stdout.write(self.style.SUCCESS(f'Total customers processed: {total_customers}'))
        self.stdout.write(self.style.SUCCESS(f'Customers updated: {updated_count}'))
        self.stdout.write(self.style.SUCCESS(f'Customers unchanged: {unchanged_count}'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
