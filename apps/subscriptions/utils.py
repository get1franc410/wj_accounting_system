# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\utils.py

from apps.subscriptions.models import Subscription

def has_production_access(user):
    """Check if user's subscription plan includes production management features."""
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    company = user.company
    if not company:
        return False
    
    subscription = company.active_subscription
    if not subscription:
        return False
    
    # Only DELUXE and PREMIUM plans have production features
    return subscription.plan in [Subscription.Plan.DELUXE, Subscription.Plan.PREMIUM]