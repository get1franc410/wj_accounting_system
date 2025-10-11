# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\management\commands\send_smart_debtor_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q, F  # Add F import
from datetime import timedelta
from decimal import Decimal

from apps.core.models import Company
from apps.backup.models import BackupSettings, DebtorReminderLog
from apps.transactions.models import Transaction
from apps.core.email_utils import send_email
from apps.core.utils import get_currency_symbol  # Add this import


class Command(BaseCommand):
    help = 'Send smart debtor reminders based on due dates and company settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Send reminders for specific company only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force the reminder check, ignoring the last check time (for manual runs)',
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No emails will be sent'))
        
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
        
        total_reminders_sent = 0
        
        for company in companies:
            try:
                # Check if company has backup settings
                if not hasattr(company, 'backup_settings'):
                    self.stdout.write(f'Skipping {company.name}: No backup settings configured')
                    continue
                    
                settings = company.backup_settings
                if not settings.debtor_reminders_enabled:
                    self.stdout.write(f'Skipping {company.name}: Debtor reminders disabled')
                    continue
                
                # Check if it's time to check for reminders
                force_run = options.get('force', False) 
                if not force_run and not settings.is_debtor_reminder_check_due():
                    self.stdout.write(f'Skipping {company.name}: Not time for reminder check yet (automated run)')
                    continue
                
                self.stdout.write(f'Processing reminders for {company.name}...')
                
                # Get unpaid transactions with due dates (only SALE transactions for debtor reminders)
                unpaid_transactions = Transaction.objects.filter(
                    company=company,
                    transaction_type='SALE',  # Only sales for debtor reminders
                    due_date__isnull=False,
                    total_amount__gt=0
                ).exclude(
                    amount_paid__gte=F('total_amount')  # Exclude fully paid
                )
                
                today = timezone.now().date()
                reminders_sent_this_run = 0
                
                for transaction in unpaid_transactions:
                    customer = transaction.customer
                    if not customer or not customer.email:
                        continue
                    
                    days_until_due = (transaction.due_date - today).days
                    days_overdue = (today - transaction.due_date).days
                    
                    reminder_type = None
                    should_send = False
                    
                    # Before due date reminders
                    if (settings.send_before_due_enabled and 
                        days_until_due == settings.days_before_due_date and 
                        days_until_due > 0):
                        reminder_type = DebtorReminderLog.ReminderType.BEFORE_DUE
                        should_send = True
                    
                    # After due date reminders
                    elif settings.send_after_due_enabled and days_overdue > 0:
                        if days_overdue == settings.days_after_due_first:
                            reminder_type = DebtorReminderLog.ReminderType.FIRST_OVERDUE
                            should_send = True
                        elif days_overdue == settings.days_after_due_second:
                            reminder_type = DebtorReminderLog.ReminderType.SECOND_OVERDUE
                            should_send = True
                        elif days_overdue == settings.days_after_due_final:
                            reminder_type = DebtorReminderLog.ReminderType.FINAL_OVERDUE
                            should_send = True
                    
                    # Check if reminder already sent
                    if should_send and reminder_type:
                        existing_reminder = DebtorReminderLog.objects.filter(
                            transaction=transaction,
                            reminder_type=reminder_type
                        ).exists()
                        
                        if existing_reminder:
                            continue
                        
                        # Get all overdue transactions for this customer
                        customer_overdue_transactions = Transaction.objects.filter(
                            company=company,
                            customer=customer,
                            transaction_type='SALE',
                            due_date__lt=today,
                            total_amount__gt=0
                        ).exclude(
                            amount_paid__gte=F('total_amount')
                        )
                        
                        # Calculate total balances
                        all_customer_transactions = Transaction.objects.filter(
                            company=company,
                            customer=customer,
                            transaction_type='SALE',
                            total_amount__gt=0
                        ).exclude(amount_paid__gte=F('total_amount'))
                        
                        total_balance = sum(t.balance_due for t in all_customer_transactions)
                        total_overdue_balance = sum(t.balance_due for t in customer_overdue_transactions)
                        
                        # Get currency symbol
                        currency_symbol = get_currency_symbol(company.currency)
                        
                        # Prepare email context
                        context = {
                            'company': company,
                            'company_name': company.name,
                            'company_email': company.email,
                            'company_phone': company.phone,
                            'customer_name': customer.name,
                            'total_balance': total_balance,
                            'total_overdue_balance': total_overdue_balance,
                            'overdue_transactions': customer_overdue_transactions,
                            'currency_symbol': currency_symbol,
                            'reminder_type': reminder_type,
                            'days_overdue': days_overdue,
                            'days_until_due': days_until_due,
                            'current_transaction': transaction,
                        }
                        
                        # Determine subject and template based on reminder type
                        if reminder_type == DebtorReminderLog.ReminderType.BEFORE_DUE:
                            subject = f"Payment Due Soon - {company.name}"
                            template = 'emails/debtor_reminder_before_due.html'
                        elif reminder_type == DebtorReminderLog.ReminderType.FINAL_OVERDUE:
                            subject = f"FINAL NOTICE - Overdue Payment - {company.name}"
                            template = 'emails/debtor_reminder_final.html'
                        else:
                            subject = f"Payment Overdue - {company.name}"
                            template = 'emails/debtor_reminder.html'
                        
                        if dry_run:
                            self.stdout.write(
                                f'  WOULD SEND: {reminder_type} to {customer.name} ({customer.email}) '
                                f'for transaction #{transaction.id} - {currency_symbol}{transaction.balance_due}'
                            )
                        else:
                            # Send the email
                            success = send_email(
                                subject=subject,
                                template_name=template,
                                context=context,
                                to_emails=[customer.email],
                                company=company 
                            )
                            
                            if success:
                                # Log the reminder
                                DebtorReminderLog.objects.create(
                                    company=company,
                                    transaction=transaction,
                                    customer=customer,
                                    reminder_type=reminder_type,
                                    email_sent_to=customer.email
                                )
                                
                                reminders_sent_this_run += 1
                                self.stdout.write(
                                    f'  ✓ Sent {reminder_type} reminder to {customer.name} '
                                    f'for transaction #{transaction.id} - {currency_symbol}{transaction.balance_due}'
                                )
                            else:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f'  ✗ Failed to send reminder to {customer.name} '
                                        f'for transaction #{transaction.id}'
                                    )
                                )
                
                # Update last check time
                if not dry_run and not force_run:
                    settings.last_debtor_reminder_check = timezone.now()
                    settings.save(update_fields=['last_debtor_reminder_check'])
                
                total_reminders_sent += reminders_sent_this_run
                self.stdout.write(
                    f'Completed {company.name}: {reminders_sent_this_run} reminders sent'
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {company.name}: {str(e)}')
                )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN COMPLETE: Would have sent {total_reminders_sent} reminders')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully sent {total_reminders_sent} debtor reminders')
            )
