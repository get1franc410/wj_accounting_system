# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\apps.py
from django.apps import AppConfig

class SubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.subscriptions'

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver
        # Although we call it manually in the admin, this is good practice.
        import apps.subscriptions.signals
