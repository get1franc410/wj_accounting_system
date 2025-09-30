# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\views.py
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.utils import timezone
from .forms import RegistrationRequestForm
from .models import Subscription, ExchangeRate

def subscription_plans_view(request):
    """
    Public view for new companies to see plans, including the Free Trial.
    """
    current_rate = ExchangeRate.objects.filter(valid_until__gte=timezone.now()).order_by('-valid_from').first()

    plans = []
    # --- MODIFIED: Fetch all plans, including TRIAL ---
    plan_choices = Subscription.Plan.choices
    
    for plan_code, plan_name in plan_choices:
        details = Subscription.PLAN_DETAILS.get(plan_code, {})
        price_usd = details.get('price_usd', 0)
        
        plan_data = {
            'code': plan_code,
            'name': plan_name,
            'price_usd': price_usd,
            'price_ngn': (price_usd * current_rate.rate) if current_rate else None,
            'features': details.get('features', [])
        }
        plans.append(plan_data)

    context = {
        'plans': plans,
        'exchange_rate': current_rate,
        'page_title': 'Choose Your Plan'
    }
    return render(request, 'subscriptions/subscription_plans.html', context)


def subscription_register_view(request, plan_code):
    """
    Handles the registration form submission for a specific plan.
    """
    plan_code = plan_code.upper()
    valid_plans = [plan[0] for plan in Subscription.Plan.choices]
    if plan_code not in valid_plans:
        raise Http404("Subscription plan not found.")

    plan_details = {
        'code': plan_code,
        'name': Subscription.Plan(plan_code).label
    }

    if request.method == 'POST':
        # --- MODIFIED: Pass plan_code to the form ---
        form = RegistrationRequestForm(request.POST, request.FILES, plan_code=plan_code)
        if form.is_valid():
            registration_request = form.save(commit=False)
            registration_request.plan = plan_details['code']
            
            # --- NEW: Set years_paid to 0 for trials ---
            if plan_code == Subscription.Plan.TRIAL:
                registration_request.years_paid = 0

            registration_request.save()
            
            messages.success(request, "Your registration request has been submitted! We will review it and get back to you shortly.")
            return redirect('auth:login')
    else:
        # --- MODIFIED: Pass plan_code to the form ---
        form = RegistrationRequestForm(plan_code=plan_code)

    context = {
        'form': form,
        'plan': plan_details,
        'page_title': f'Register for {plan_details["name"]}'
    }
    return render(request, 'subscriptions/register_form.html', context)


@login_required
def subscription_status(request):
    """
    Displays the current subscription status for the logged-in user's company.
    
    FIX: The redirect for valid subscriptions has been removed. This allows users
    to view their subscription details (like expiry date) at any time.
    """
    # Ensure the user has a company context before proceeding
    if not hasattr(request.user, 'company') or not request.user.company:
         # This can happen for superusers or misconfigured accounts.
         # Redirect them to a safe page or show an error.
        messages.error(request, "Your user account is not associated with a company.")
        return redirect('auth:login')

    subscription = Subscription.objects.filter(company=request.user.company).first()
    
    # The problematic redirect has been removed from here.
    # The view will now always render the status page for logged-in users.

    context = {
        'subscription': subscription,
        'page_title': 'Subscription Status'
    }
    return render(request, 'subscriptions/status.html', context)
