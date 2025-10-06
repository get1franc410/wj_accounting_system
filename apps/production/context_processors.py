# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\production\context_processors.py

def production_access(request):
    """
    Add production access context variable to all templates.
    """
    has_access = False
    
    # Check if user is authenticated
    if request.user.is_authenticated:
        # Check if user has a subscription with production access
        if hasattr(request.user, 'subscription'):
            subscription = request.user.subscription
            # Production module is available in Deluxe and Premium plans
            if subscription.plan_code in ['DELUXE', 'PREMIUM']:
                has_access = True
        
        # Admins always have access
        if request.user.user_type == 'ADMIN':
            has_access = True
    
    return {
        'has_production_access': has_access
    }
