# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\journal\management\commands\validate_journal_entries.py

from django.core.management.base import BaseCommand
from django.db.models import Sum
from apps.journal.models import JournalEntry
from apps.core.models import Company
from decimal import Decimal

class Command(BaseCommand):
    help = 'Validate and fix unbalanced journal entries'

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, help='Company ID to validate')
        parser.add_argument('--fix', action='store_true', help='Attempt to fix unbalanced entries')

    def handle(self, *args, **options):
        companies = Company.objects.all()
        if options['company_id']:
            companies = companies.filter(id=options['company_id'])

        for company in companies:
            self.stdout.write(f"\nValidating entries for {company.name}...")
            
            entries = JournalEntry.objects.filter(company=company)
            unbalanced_entries = []
            
            for entry in entries:
                totals = entry.lines.aggregate(
                    total_debit=Sum('debit'),
                    total_credit=Sum('credit')
                )
                
                total_debits = totals.get('total_debit') or Decimal('0.00')
                total_credits = totals.get('total_credit') or Decimal('0.00')
                
                if total_debits != total_credits:
                    difference = total_debits - total_credits
                    unbalanced_entries.append({
                        'entry': entry,
                        'debits': total_debits,
                        'credits': total_credits,
                        'difference': difference
                    })
                    
                    self.stdout.write(
                        self.style.ERROR(
                            f"Unbalanced Entry JE-{entry.id}: "
                            f"Debits={total_debits}, Credits={total_credits}, "
                            f"Difference={difference}"
                        )
                    )
            
            if not unbalanced_entries:
                self.stdout.write(
                    self.style.SUCCESS(f"All entries for {company.name} are balanced!")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Found {len(unbalanced_entries)} unbalanced entries for {company.name}"
                    )
                )
                
                if options['fix']:
                    self.stdout.write("Attempting to fix unbalanced entries...")
                    for item in unbalanced_entries:
                        # You can add logic here to attempt fixes
                        # For now, just report them
                        pass
