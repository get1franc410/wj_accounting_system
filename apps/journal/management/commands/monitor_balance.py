# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\journal\management\commands\monitor_balance.py

from django.core.management.base import BaseCommand
from django.db.models import Sum
from apps.journal.models import JournalEntry
from apps.core.models import Company
from decimal import Decimal

class Command(BaseCommand):
    help = 'Monitor for unbalanced journal entries'

    def handle(self, *args, **options):
        companies = Company.objects.all()
        
        for company in companies:
            entries = JournalEntry.objects.filter(company=company).order_by('-id')[:10]  # Check last 10 entries
            unbalanced_count = 0
            
            for entry in entries:
                totals = entry.lines.aggregate(
                    total_debit=Sum('debit'),
                    total_credit=Sum('credit')
                )
                
                total_debits = totals.get('total_debit') or Decimal('0.00')
                total_credits = totals.get('total_credit') or Decimal('0.00')
                
                if total_debits != total_credits:
                    difference = total_debits - total_credits
                    unbalanced_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"NEW Unbalanced Entry JE-{entry.id}: "
                            f"Debits={total_debits}, Credits={total_credits}, "
                            f"Difference={difference}"
                        )
                    )
            
            if unbalanced_count == 0:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Recent entries for {company.name} are balanced!")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Found {unbalanced_count} new unbalanced entries for {company.name}")
                )
