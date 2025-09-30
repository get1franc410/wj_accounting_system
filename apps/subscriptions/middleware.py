# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from .models import Subscription

class SubscriptionValidationMiddleware:
    """
    Middleware to validate the company's subscription on each request.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [
            reverse('auth:login'),
            reverse('auth:logout'),
            reverse('subscriptions:status'),
            reverse('subscriptions:register'),
        ]
        self.exempt_paths = ['/admin/', '/static/', '/media/']

    def __call__(self, request):
        # Skip validation for exempt URLs and paths
        if request.path_info in self.exempt_urls or any(request.path.startswith(path) for path in self.exempt_paths):
            return self.get_response(request)

        # Skip for unauthenticated users (they will be redirected by @login_required)
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Superusers are always exempt
        if request.user.is_superuser:
            return self.get_response(request)

        # Main validation logic
        company = request.user.company
        if not company:
            messages.error(request, "Your user account is not associated with a company.")
            return redirect('auth:login')

        try:
            subscription = company.subscription
            if not subscription.is_valid():
                messages.warning(request, "Your subscription is inactive or has expired. Please contact support.")
                return redirect('subscriptions:status')
        except Subscription.DoesNotExist:
            messages.error(request, "No active subscription found for your company. Please contact support.")
            return redirect('subscriptions:status')
        
        return self.get_response(request)
