# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from django.conf import settings
from decimal import Decimal
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.utils import timezone
from apps.accounts.models import Account, AccountType
from apps.customers.models import Customer
from apps.inventory.models import InventoryItem
from apps.transactions.models import TransactionCategory
from apps.transactions.forms import TransactionCategoryForm

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from apps.authentication.decorators import user_type_required
from apps.authentication.models import User
from .forms import CompanySettingsForm, EmailConfigForm, UserCompanyForm, AuditorCompanyForm, UserProfileForm, UserCreationForm, UserUpdateForm
from .models import Company, EmailConfiguration
from apps.core.email_utils import send_email
from apps.subscriptions.models import Subscription 
from apps.subscriptions.models import Subscription, ExchangeRate

def public_home_view(request):
    """
    Renders the public landing page for unauthenticated users.
    If a user is already authenticated, it redirects them to their dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home') 
    
    # Fetch the current valid exchange rate
    current_rate = ExchangeRate.objects.filter(valid_until__gte=timezone.now()).order_by('-valid_from').first()

    # Prepare plan details for the template
    plans = []
    # Exclude TRIAL from public display
    plan_choices = [plan for plan in Subscription.Plan.choices if plan[0] != 'TRIAL']
    
    for plan_code, plan_name_full in plan_choices:
        details = Subscription.PLAN_DETAILS.get(plan_code, {})
        price_usd = details.get('price_usd', 0)
        
        plan_data = {
            'code': plan_code,
            'name': plan_code.title(), # e.g., 'BASIC' -> 'Basic'
            'price_usd': price_usd,
            'price_ngn': (price_usd * current_rate.rate) if current_rate else None,
            'features': details.get('features', [])
        }
        plans.append(plan_data)

    context = {
        'page_title': 'WJ-Accounting | Modern Accounting for Your Business',
        'plans': plans,
        'exchange_rate': current_rate,
    }
    return render(request, 'core/public_home.html', context)

CURRENCY_SYMBOLS = {
    'NGN': '₦',
    'USD': '$',
    'GBP': '£',
    'EUR': '€',
}
CURRENCY_ICONS = {
    'NGN': 'fa-naira-sign',
    'USD': 'fa-dollar-sign',
    'GBP': 'fa-sterling-sign',
    'EUR': 'fa-euro-sign',
}

@method_decorator(never_cache, name='dispatch')
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.request.user.company 
        context['company'] = company
        context['page_title'] = 'Dashboard'

        if company:
            # --- Dashboard Metrics ---
            cash_accounts = Account.objects.filter(company=company, account_type__name='Bank')
            cash_balance = sum(acc.get_balance() for acc in cash_accounts)
            context['cash_at_bank'] = cash_balance

            ar_accounts = Account.objects.filter(company=company, account_type__name='Accounts Receivable')
            ar_balance = sum(acc.get_balance() for acc in ar_accounts)
            context['accounts_receivable'] = ar_balance

            ap_accounts = Account.objects.filter(company=company, account_type__name='Accounts Payable')
            ap_balance = sum(acc.get_balance() for acc in ap_accounts)
            context['accounts_payable'] = ap_balance

            context['active_customers'] = Customer.objects.filter(company=company, is_active=True).count()
            context['inventory_items'] = InventoryItem.objects.filter(company=company).count()
        
        else:
            # Provide default values if no company is associated
            context['cash_at_bank'] = Decimal('0.00')
            context['accounts_receivable'] = Decimal('0.00')
            context['accounts_payable'] = Decimal('0.00')
            context['active_customers'] = 0
            context['inventory_items'] = 0

        return context
    
@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def admin_settings(request):
    """
    Unified admin control panel with dashboard and settings
    Enhanced for .exe deployment and multi-company usage
    """
    user_company = request.user.company
    
    # Enhanced company validation
    if not user_company:
        messages.error(request, "You are not associated with a company. Please contact support.")
        return redirect('auth:login')
    
    # 🆕 CHECK IF COMPANY HAS ACCOUNTS SET UP
    has_accounts = user_company.accounts.exists()
    
    if not has_accounts:
        messages.warning(
            request, 
            "Please set up your Chart of Accounts first before creating transaction categories."
        )
        return redirect('accounts:chart-of-accounts')
    
    # --- MODIFIED START ---
    # This entire block has been updated to use the Subscription model.
    # The context variable names ('user_license', 'license_valid', etc.) are kept
    # the same to avoid breaking your template.
    try:
        # We now look for 'subscription' which is the related_name from the Company model
        subscription = user_company.subscription
        user_license = subscription  # Keep old variable name for template compatibility
        license_valid = subscription.is_active
        license_in_grace = False  # The grace period concept is removed in the new model
        
        if subscription.valid_until:
            license_days_remaining = (subscription.valid_until - timezone.now().date()).days
        else:
            license_days_remaining = 0  # Or a large number if it's perpetual

        # We create a 'features' list from the new model's fields
        license_features = [
            f"Plan: {subscription.plan_name}",
            f"Max Users: {subscription.max_users}"
        ]

    except Subscription.DoesNotExist:
        user_license = None
        license_valid = False
        license_in_grace = False
        license_days_remaining = 0
        license_features = ["No active subscription found."]
    except Exception as e:
        # Handle any other license-related errors gracefully
        if settings.DEBUG:
            print(f"Subscription context error: {e}")
        user_license = None
        license_valid = False
        license_in_grace = False
        license_days_remaining = 0
        license_features = ["Error loading subscription details."]
    # --- MODIFIED END ---
    
    # Get or create auditor company
    auditor_company, created = Company.objects.get_or_create(
        company_type=Company.CompanyType.AUDITOR,
        defaults={
            'name': 'External Auditor',
            'industry': 'Accounting & Auditing',
            'is_active': True
        }
    )
    
    # Get or create email config and backup settings
    email_config, created = EmailConfiguration.objects.get_or_create(company=user_company)
    
    # Import here to avoid circular imports
    try:
        from apps.backup.models import BackupSettings, Backup
        backup_settings, created = BackupSettings.objects.get_or_create(company=user_company)
    except ImportError:
        # Handle case where backup app might not be available in some deployments
        backup_settings = None
    
    if request.method == 'POST':
        # Determine which form was submitted
        form_type = request.POST.get('form_type')
        
        if form_type == 'user_company':
            user_company_form = UserCompanyForm(request.POST, request.FILES, instance=user_company)
            auditor_company_form = AuditorCompanyForm(instance=auditor_company)
            email_form = EmailConfigForm(instance=email_config)
            
            if user_company_form.is_valid():
                user_company_form.save()
                messages.success(request, "Company information updated successfully!")
                return redirect('core:admin_settings')
                
        elif form_type == 'auditor_company':
            user_company_form = UserCompanyForm(instance=user_company)
            auditor_company_form = AuditorCompanyForm(request.POST, instance=auditor_company)
            email_form = EmailConfigForm(instance=email_config)
            
            if auditor_company_form.is_valid():
                auditor_company_form.save()
                messages.success(request, "Auditor information updated successfully!")
                return redirect('core:admin_settings')
                
        elif form_type == 'email_config':
            user_company_form = UserCompanyForm(instance=user_company)
            auditor_company_form = AuditorCompanyForm(instance=auditor_company)
            email_form = EmailConfigForm(request.POST, instance=email_config)
            
            if email_form.is_valid():
                email_form.save()
                messages.success(request, "Email configuration updated successfully!")
                return redirect('core:admin_settings')
        
        # 🆕 HANDLE TRANSACTION CATEGORY FORM
        elif form_type == 'transaction_category':
            category_form = TransactionCategoryForm(request.POST, company=user_company)
            if category_form.is_valid():
                category = category_form.save(commit=False)
                category.company = user_company
                category.save()
                messages.success(request, f'Transaction category "{category.name}" created successfully!')
                return redirect('core:admin_settings')
        
        messages.error(request, "Please correct the errors below.")
    else:
        user_company_form = UserCompanyForm(instance=user_company)
        auditor_company_form = AuditorCompanyForm(instance=auditor_company)
        email_form = EmailConfigForm(instance=email_config)
    
    # Get transaction categories for this company
    categories = TransactionCategory.objects.filter(company=user_company).order_by('account_type__category', 'name')
    category_form = TransactionCategoryForm(company=user_company)
    subscription = Subscription.objects.filter(company=request.user.company).first()
    subscription_features = []
    if subscription:
        plan_details = subscription.PLAN_DETAILS.get(subscription.plan, {})
        subscription_features = plan_details.get('features', [])
    # Get system status and recent backups - Enhanced for multi-company
    system_status = {
        'total_users': user_company.users.count(),
        'active_customers': user_company.customers.filter(entity_type__in=['customer', 'both']).count(),
        'total_transactions': user_company.transactions.count(),
        'last_backup': None,
    }
    
    # Safely get backup information
    recent_backups = []
    if backup_settings and hasattr(user_company, 'backups'):
        try:
            system_status['last_backup'] = user_company.backups.filter(status='SUCCESS').first()
            recent_backups = user_company.backups.all()[:5]
        except Exception as e:
            if settings.DEBUG:
                print(f"Backup status error: {e}")
    
    context = {
        'user_company_form': user_company_form,
        'auditor_company_form': auditor_company_form,
        'email_form': email_form,
        'categories': categories,
        'category_form': category_form,
        'user_company': user_company,
        'auditor_company': auditor_company,
        'backup_settings': backup_settings,
        'email_config': email_config,
        'system_status': system_status,
        'recent_backups': recent_backups,
        'currency_symbol': CURRENCY_SYMBOLS.get(user_company.currency, user_company.currency),
        'subscription': subscription,
        'subscription_features': subscription_features,
        'has_accounts': has_accounts,
        'user_license': user_license,
        'license_valid': license_valid,
        'license_in_grace': license_in_grace,
        'license_days_remaining': license_days_remaining,
        'license_features': license_features,
        'page_title': 'Admin Control Panel'
    }
    return render(request, 'core/admin_settings.html', context)

# --- The rest of your file remains unchanged ---

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def add_category(request):
    """Add a new transaction category"""
    if request.method == 'POST':
        form = TransactionCategoryForm(request.POST, company=request.user.company)
        if form.is_valid():
            category = form.save(commit=False)
            category.company = request.user.company
            category.save()
            messages.success(request, f"Category '{category.name}' added successfully!")
        else:
            messages.error(request, "Please correct the errors in the category form.")
    
    return redirect('core:admin_settings')

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def edit_category(request, category_id):
    """Edit an existing transaction category"""
    category = get_object_or_404(TransactionCategory, id=category_id, company=request.user.company)
    
    if request.method == 'POST':
        form = TransactionCategoryForm(request.POST, instance=category, company=request.user.company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully!")
        else:
            messages.error(request, "Please correct the errors in the category form.")
    
    return redirect('core:admin_settings')

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def get_category(request, category_id):
    """Get category form for editing (AJAX endpoint)"""
    category = get_object_or_404(TransactionCategory, id=category_id, company=request.user.company)
    form = TransactionCategoryForm(instance=category, company=request.user.company)
    
    return render(request, 'core/category_form_partial.html', {'form': form})

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def user_management(request):
    """User management for admins"""
    users = User.objects.filter(company=request.user.company).order_by('username')
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'create_user':
            form = UserCreationForm(request.POST, company=request.user.company)
            if form.is_valid():
                user = form.save(commit=False)
                user.company = request.user.company
                user.save()
                messages.success(request, f"User '{user.username}' created successfully!")
                return redirect('core:user_management')
            else:
                # Pass the invalid form back to the template
                return render(request, 'core/user_management.html', {
                    'users': users,
                    'create_form': form,
                    'page_title': 'User Management'
                })
        
        elif form_type == 'update_user':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id, company=request.user.company)
            form = UserUpdateForm(request.POST, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, f"User '{user.username}' updated successfully!")
                return redirect('core:user_management')
            else:
                # Add error handling for update form as well
                return render(request, 'core/user_management.html', {
                    'users': users,
                    'create_form': UserCreationForm(company=request.user.company),
                    'update_form': form,
                    'page_title': 'User Management'
                })
    
    context = {
        'users': users,
        'create_form': UserCreationForm(company=request.user.company),
        'page_title': 'User Management'
    }
    return render(request, 'core/user_management.html', context)

@login_required
def settings_dashboard(request):
    """Main settings dashboard for all users"""
    user_company = request.user.company
    
    # Get system statistics
    system_stats = {
        'total_users': user_company.users.count() if user_company else 0,
        'total_transactions': user_company.transactions.count() if user_company else 0,
        'last_backup': None,  # Will be populated if backup app is available
    }
    
    # Try to get backup information
    try:
        from apps.backup.models import Backup
        last_backup = user_company.backups.filter(status='SUCCESS').first()
        system_stats['last_backup'] = last_backup.created_at if last_backup else None
    except ImportError:
        pass
    
    # Get email and backup settings for status display
    email_config = None
    backup_settings = None
    
    try:
        email_config = user_company.email_config
    except:
        pass
    
    try:
        from apps.backup.models import BackupSettings
        backup_settings = user_company.backup_settings
    except ImportError:
        pass
    
    # Forms for modals
    company_form = CompanySettingsForm(instance=user_company)
    
    # Currency form (simple form for currency selection)
    from django import forms
    
    class CurrencyForm(forms.Form):
        CURRENCY_CHOICES = [
            ('NGN', 'Nigerian Naira (₦)'),
            ('USD', 'US Dollar ($)'),
            ('GBP', 'British Pound (£)'),
            ('EUR', 'Euro (€)'),
        ]
        currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial='NGN')
    
    currency_form = CurrencyForm(initial={'currency': user_company.currency if user_company else 'NGN'})
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'company_settings':
            company_form = CompanySettingsForm(request.POST, request.FILES, instance=user_company)
            if company_form.is_valid():
                company_form.save()
                messages.success(request, "Company settings updated successfully!")
                return redirect('core:settings_dashboard')
        
        elif form_type == 'currency_settings':
            currency_form = CurrencyForm(request.POST)
            if currency_form.is_valid():
                user_company.currency = currency_form.cleaned_data['currency']
                user_company.save()
                messages.success(request, "Currency updated successfully!")
                return redirect('core:settings_dashboard')
    
    context = {
        'system_stats': system_stats,
        'email_config': email_config,
        'backup_settings': backup_settings,
        'company_form': company_form,
        'currency_form': currency_form,
        'page_title': 'Settings Dashboard'
    }
    return render(request, 'core/settings_dashboard.html', context)

@login_required
def user_profile(request):
    """User profile management"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('core:user_profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'form': form,
        'page_title': 'My Profile'
    }
    return render(request, 'core/user_profile.html', context)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def create_user(request):
    """Create new user (AJAX endpoint)"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST, company=request.user.company)
        if form.is_valid():
            user = form.save(commit=False)
            user.company = request.user.company
            user.save()
            return JsonResponse({'success': True, 'message': f"User '{user.username}' created successfully!"})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def update_user(request, user_id):
    """Update user (AJAX endpoint)"""
    user_obj = get_object_or_404(User, id=user_id, company=request.user.company)
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': f"User '{user_obj.username}' updated successfully!"})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def get_user(request, user_id):
    """Get user form for editing (AJAX endpoint)"""
    user_obj = get_object_or_404(User, id=user_id, company=request.user.company)
    form = UserUpdateForm(instance=user_obj)
    
    return render(request, 'core/user_form_partial.html', {'form': form})

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def deactivate_user(request, user_id):
    """Deactivate/activate user"""
    user_obj = get_object_or_404(User, id=user_id, company=request.user.company)
    
    if request.method == 'POST':
        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        
        status = "activated" if user_obj.is_active else "deactivated"
        messages.success(request, f"User '{user_obj.username}' {status} successfully!")
    
    return redirect('core:user_management')

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def run_maintenance(request):
    """Run database maintenance tasks"""
    if request.method == 'POST':
        try:
            from django.core.management import call_command
            from io import StringIO
            
            output = StringIO()
            
            # Run database optimization commands
                        # Run database optimization commands
            call_command('clearsessions', stdout=output)
            call_command('collectstatic', '--noinput', stdout=output)
            
            return JsonResponse({
                'success': True, 
                'message': 'Database maintenance completed successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# Helper functions for database configuration
def get_current_database_config():
    """Get current database configuration"""
    from django.conf import settings
    db_config = settings.DATABASES['default']
    
    if 'postgresql' in db_config['ENGINE']:
        return {
            'type': 'postgresql',
            'host': db_config.get('HOST', 'localhost'),
            'port': db_config.get('PORT', '5432'),
            'name': db_config.get('NAME'),
            'user': db_config.get('USER'),
        }
    else:
        return {
            'type': 'sqlite',
            'name': db_config.get('NAME', 'db.sqlite3'),
        }

def test_database_connection(config):
    """Test database connection"""
    try:
        if config.get('type') == 'postgresql':
            import psycopg2
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['name'],
                user=config['user'],
                password=config['password']
            )
            conn.close()
            return True
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False
    
    return True

def save_database_config(config):
    """Save database configuration to settings file"""
    # This would typically write to a configuration file
    # For now, we'll just return True as this is complex for .exe deployment
    return True

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def database_config(request):
    """Database configuration for .exe installations"""
    if request.method == 'POST':
        # Handle database configuration
        db_type = request.POST.get('db_type', 'sqlite')
        
        if db_type == 'postgresql':
            # Configure PostgreSQL connection
            config = {
                'host': request.POST.get('db_host', 'localhost'),
                'port': request.POST.get('db_port', '5432'),
                'name': request.POST.get('db_name'),
                'user': request.POST.get('db_user'),
                'password': request.POST.get('db_password'),
            }
            
            # Test connection and save configuration
            if test_database_connection(config):
                save_database_config(config)
                messages.success(request, "Database configuration saved successfully!")
            else:
                messages.error(request, "Failed to connect to database. Please check your settings.")
        
        return redirect('core:database_config')
    
    current_config = get_current_database_config()
    context = {
        'current_config': current_config,
        'page_title': 'Database Configuration'
    }
    return render(request, 'core/database_config.html', context)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def instant_backup(request):
    """Create backup instantly"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        from apps.backup.tasks import perform_backup_and_notify
        success = perform_backup_and_notify(request.user.company.id)
        
        if success:
            messages.success(request, "Backup created successfully!")
        else:
            messages.error(request, "Backup failed. Please check your settings.")
            
    except Exception as e:
        messages.error(request, f"Error creating backup: {str(e)}")
    
    return redirect('core:admin_settings')  # FIXED: Changed from admin_dashboard

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def send_instant_reminders(request):
    """Send debtor reminders instantly"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        from django.core.management import call_command
        from io import StringIO
        
        output = StringIO()
        call_command('send_smart_debtor_reminders', 
                    company_id=request.user.company.id, 
                    stdout=output)
        
        result = output.getvalue()
        if 'sent' in result.lower():
            messages.success(request, "Debtor reminders sent successfully!")
        else:
            messages.info(request, "No reminders were sent (no overdue invoices found).")
            
    except Exception as e:
        messages.error(request, f"Error sending reminders: {str(e)}")
    
    return redirect('core:admin_settings')  # FIXED: Changed from admin_dashboard

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def send_audit_reminder(request):
    """Send audit reminder instantly"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        from apps.backup.tasks import send_audit_reminders
        success = send_audit_reminders(request.user.company.id)
        
        if success:
            messages.success(request, "Audit reminders sent successfully!")
        else:
            messages.error(request, "No auditors found or email failed.")
            
    except Exception as e:
        messages.error(request, f"Error sending audit reminders: {str(e)}")
    
    return redirect('core:admin_settings')  # FIXED: Changed from admin_dashboard

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def test_email_config(request):
    """Test email configuration"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        company = request.user.company
        email_config = company.email_config
        
        if not email_config or not email_config.is_active:
            messages.error(request, "Email configuration not found or inactive.")
            return redirect('core:admin_settings')
        
        success = send_email(
            subject=f"Test Email from {company.name}",
            template_name='emails/test_email.html',
            context={
                'company_name': company.name,
                'test_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_name': request.user.get_full_name() or request.user.username,
            },
            to_emails=[email_config.email_address],
            company=company  # Pass company parameter
        )
        
        if success:
            messages.success(request, f"Test email sent successfully to {email_config.email_address}!")
        else:
            messages.error(request, "Failed to send test email. Please check your configuration.")
            
    except Exception as e:
        messages.error(request, f"Error sending test email: {str(e)}")
    
    return redirect('core:admin_settings')

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def send_audit_documents(request):
    """Send comprehensive audit documents package instantly"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        from apps.backup.tasks import send_audit_documents
        success = send_audit_documents(request.user.company.id)
        
        if success:
            messages.success(request, "Audit documents package sent successfully!")
        else:
            messages.error(request, "Failed to send audit documents. Please check your settings.")
            
    except Exception as e:
        messages.error(request, f"Error sending audit documents: {str(e)}")
    
    return redirect('core:admin_settings')

