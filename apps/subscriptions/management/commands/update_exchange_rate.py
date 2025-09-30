# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\management\commands\update_exchange_rate.py
import requests
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.subscriptions.models import ExchangeRate

# Using a free, no-key-required API for simplicity.
# For production, consider a more robust service with an API key.
API_URL = "https://v6.exchangerate-api.com/v6/YOUR_API_KEY/latest/USD"
# Get a free key from: https://www.exchangerate-api.com/

class Command(BaseCommand):
    help = 'Fetches and updates the USD to NGN exchange rate.'

    def handle(self, *args, **options):
        self.stdout.write("Fetching latest exchange rate for USD to NGN...")

        try:
            # IMPORTANT: Replace YOUR_API_KEY with your actual key from exchangerate-api.com
            response = requests.get(API_URL.replace("YOUR_API_KEY", "9e79f4036da380b2e9e391a3")) # Replace with your key
            response.raise_for_status()
            data = response.json()

            if data.get('result') == 'success' and 'NGN' in data.get('conversion_rates', {}):
                rate = data['conversion_rates']['NGN']

                # Calculate the validity period for the current week (Monday to Sunday)
                today = timezone.now().date()
                start_of_week = today - timedelta(days=today.weekday())
                end_of_week = start_of_week + timedelta(days=6)

                valid_from_dt = timezone.make_aware(timezone.datetime.combine(start_of_week, timezone.datetime.min.time()))
                valid_until_dt = timezone.make_aware(timezone.datetime.combine(end_of_week, timezone.datetime.max.time()))

                # Update or create the rate
                rate_obj, created = ExchangeRate.objects.update_or_create(
                    currency_pair="USD_NGN",
                    valid_from__date=start_of_week,
                    defaults={
                        'rate': rate,
                        'valid_from': valid_from_dt,
                        'valid_until': valid_until_dt,
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Successfully created new rate: 1 USD = {rate} NGN. Valid until {end_of_week}."))
                else:
                    self.stdout.write(self.style.SUCCESS(f"Successfully updated rate: 1 USD = {rate} NGN. Valid until {end_of_week}."))

            else:
                self.stderr.write(self.style.ERROR("Failed to get NGN rate from API response."))

        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"API request failed: {e}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
