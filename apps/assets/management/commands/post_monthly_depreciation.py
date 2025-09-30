# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\assets\management\commands\post_monthly_depreciation.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Company
from apps.assets.models import Asset
from apps.assets.services import post_depreciation_for_asset
from dateutil.relativedelta import relativedelta

class Command(BaseCommand):
    help = 'Calculates and posts depreciation for all active assets for the previous month.'

    def handle(self, *args, **options):
        # This command should be run at the beginning of a month to post for the previous month.
        today = timezone.now().date()
        # Get the last day of the previous month.
        post_date = today.replace(day=1) - relativedelta(days=1)

        self.stdout.write(f"--- Starting Depreciation Posting for {post_date.strftime('%B %Y')} ---")

        active_companies = Company.objects.filter(is_active=True) # Assuming Company has an 'is_active' flag
        if not active_companies.exists():
            self.stdout.write(self.style.WARNING("No active companies found."))
            return

        for company in active_companies:
            self.stdout.write(self.style.SUCCESS(f"\nProcessing company: {company.name}"))
            
            # Find assets that are active (purchased before the post date) and not fully depreciated.
            assets_to_process = Asset.objects.filter(
                company=company,
                purchase_date__lte=post_date
            )

            if not assets_to_process.exists():
                self.stdout.write("No assets requiring depreciation found for this company.")
                continue

            for asset in assets_to_process:
                # Check if asset has already reached its salvage value
                if asset.current_book_value <= asset.salvage_value:
                    self.stdout.write(f"  - Skipping {asset.name}: Already at or below salvage value.")
                    continue

                # Call the service to perform the posting
                journal_entry, message = post_depreciation_for_asset(asset, post_date)
                
                if journal_entry:
                    self.stdout.write(self.style.SUCCESS(f"  - SUCCESS: {message} (JE ID: {journal_entry.id})"))
                else:
                    # Display info or warning messages without failing the whole command
                    self.stdout.write(self.style.WARNING(f"  - INFO: {message}"))

        self.stdout.write("\n--- Depreciation Posting Complete ---")

