# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\management\commands\send_debtor_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import F
from apps.core.models import Company
from apps.customers.models import Customer
from apps.transactions.models import Transaction
from apps.core.email_utils import send_email
from apps.core.utils import get_currency_symbol  # Import centralized function
from datetime import date

class Command(BaseCommand):
    help = 'Send payment reminders to customers with overdue invoices'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Specific company ID to process'
        )
        parser.add_argument(
            '--min-days-overdue',
            type=int,
            default=7,
            help='Minimum days overdue before sending reminder'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails'
        )
    
    def handle(self, *args, **options):
        company_id = options.get('company_id')
        min_days_overdue = options.get('min_days_overdue', 7)
        dry_run = options.get('dry_run', False)
        
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
            self.stdout.write(self.style.WARNING("No active user companies found."))
            return
        
        total_sent = 0
        total_failed = 0
        
        for company in companies:
            self.stdout.write(f"\nProcessing company: {company.name}")
            
            if dry_run:
                self.stdout.write(self.style.WARNING("DRY RUN - No emails will be sent"))
            
            # Find customers with overdue invoices
            today = timezone.now().date()
            cutoff_date = today - timezone.timedelta(days=min_days_overdue)
            
            customers_with_overdue = Customer.objects.filter(
                company=company,
                entity_type__in=[Customer.CUSTOMER, Customer.BOTH],
                email__isnull=False,
                transactions__transaction_type=Transaction.SALE,
                transactions__due_date__lt=today,
                transactions__due_date__lte=cutoff_date
            ).exclude(
                transactions__amount_paid__gte=F('transactions__total_amount')
            ).distinct()
            
            company_sent = 0
            company_failed = 0
            
            for customer in customers_with_overdue:
                # Get overdue transactions for this customer
                overdue_transactions = Transaction.objects.filter(
                    company=company,
                    customer=customer,
                    transaction_type=Transaction.SALE,
                    due_date__lt=today,
                    due_date__lte=cutoff_date
                ).exclude(
                    amount_paid__gte=F('total_amount')
                )
                
                if not overdue_transactions.exists():
                    continue
                
                # Calculate totals
                total_overdue_balance = sum(t.balance_due for t in overdue_transactions)
                total_balance = customer.receivable_balance
                
                # Get currency symbol using centralized utility
                currency_symbol = get_currency_symbol(company.currency)
                
                if dry_run:
                    self.stdout.write(
                        f"  Would send reminder to {customer.name} "
                        f"({customer.email}) for {overdue_transactions.count()} "
                        f"overdue invoices totaling {currency_symbol}{total_overdue_balance}"
                    )
                    company_sent += 1
                    continue
                
                # Send the email
                try:
                    success = send_email(
                        subject=f"Payment Reminder from {company.name}",
                        template_name='emails/debtor_reminder.html',
                        context={
                            'company': company,
                            'company_name': company.name,
                            'company_email': company.email,
                            'company_phone': company.phone,
                            'customer_name': customer.name,
                            'total_balance': total_balance,
                            'total_overdue_balance': total_overdue_balance,
                            'overdue_transactions': overdue_transactions,
                            'currency_symbol': currency_symbol,
                        },
                        to_emails=[customer.email]
                    )
                    
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ Sent reminder to {customer.name} "
                                f"for {overdue_transactions.count()} overdue invoices"
                            )
                        )
                        company_sent += 1
                    else:
                        self.stdout.write(
                            self.style.ERROR(f"  ✗ Failed to send reminder to {customer.name}")
                        )
                        company_failed += 1
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Error sending to {customer.name}: {str(e)}")
                    )
                    company_failed += 1
            
            self.stdout.write(
                f"Company {company.name} results: {company_sent} sent, {company_failed} failed"
            )
            total_sent += company_sent
            total_failed += company_failed
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n=== SUMMARY ===\n"
                f"Total reminders sent: {total_sent}\n"
                f"Total failures: {total_failed}\n"
                f"Companies processed: {companies.count()}"
            )
        )
