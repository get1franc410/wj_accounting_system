# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\signals.py
import secrets
import string
import random  # <-- ACTION: Import the random module
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.core.management import call_command
from django.db import transaction

from .models import RegistrationRequest, Subscription
from apps.core.models import Company
from apps.authentication.models import User
from apps.core.email_utils import send_email

def generate_random_password(length=12):
    """Generates a secure random password."""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for i in range(length))

# --- ACTION: NEW FUNCTION TO GENERATE UNIQUE USERNAMES ---
def generate_username(full_name):
    """
    Generates a unique username based on the user's full name.
    Format: [FirstInitial][LastName][4-digit-number], max 11 chars.
    Example: 'Adeyanju Joshua' -> 'ajoshua1234'
    """
    try:
        parts = full_name.strip().split()
        if not parts:
            # Fallback for empty name
            first_name = "user"
            last_name = ""
        else:
            first_name = parts[0]
            last_name = "".join(parts[1:]) # Join remaining parts for last name

        # Create the base username, clean it, and truncate
        base = (first_name[0] + last_name).lower()
        base = ''.join(filter(str.isalnum, base)) # Remove non-alphanumeric chars
        base = base[:7] # Truncate to 7 characters to leave space for numbers

        # Generate a username and check for uniqueness
        while True:
            # Generate a random 4-digit number
            suffix = str(random.randint(1000, 9999))
            username = base + suffix
            
            # Check if this username already exists
            if not User.objects.filter(username=username).exists():
                return username # It's unique, so we can use it
    except Exception:
        # Broad fallback in case of any unexpected name format
        return "user" + str(random.randint(10000, 99999))


def approve_registration_request(sender, instance, created, **kwargs):
    """
    Handles the logic after a registration request is approved.
    This now automatically seeds the new company and creates a custom username.
    """
    # Ensure this runs only when an existing request is moved to APPROVED
    if instance.status == RegistrationRequest.Status.APPROVED and not created:
        
        with transaction.atomic():
            if Company.objects.filter(name__iexact=instance.company_name).exists():
                instance.admin_notes = f"Approval failed: A company named '{instance.company_name}' already exists."
                instance.status = RegistrationRequest.Status.REJECTED
                instance.save()
                return

            activation_date = timezone.now()
            admin_note_suffix = ""

            if instance.plan == Subscription.Plan.TRIAL:
                duration_days = Subscription.PLAN_DETAILS.get('TRIAL', {}).get('duration_days', 30)
                expiry_date = activation_date + timedelta(days=duration_days)
                admin_note_suffix = f"Approved for a {duration_days}-day Trial."
            else:
                years_to_add = instance.years_paid if instance.years_paid > 0 else 1
                expiry_date = activation_date + timedelta(days=365 * years_to_add)
                admin_note_suffix = f"Approved for {years_to_add} year(s)."

            company = Company.objects.create(name=instance.company_name, email=instance.contact_email, phone=instance.contact_phone)
            
            # --- ACTION: GENERATE THE NEW USERNAME AND PASSWORD ---
            new_username = generate_username(instance.contact_name)
            temp_password = generate_random_password()

            # --- ACTION: USE THE NEWLY GENERATED USERNAME ---
            admin_user = User.objects.create_user(
                username=new_username, # Use the generated username
                email=instance.contact_email, 
                password=temp_password,
                first_name=instance.contact_name.split(' ')[0],
                last_name=' '.join(instance.contact_name.split(' ')[1:]) if ' ' in instance.contact_name else '',
                company=company, 
                user_type=User.UserType.ADMIN, 
                is_staff=False, 
                is_superuser=False, 
                force_password_change=True
            )
            
            subscription = Subscription.objects.create(
                company=company,
                plan=instance.plan,
                status=Subscription.Status.ACTIVE,
                activated_on=activation_date,
                expires_on=expiry_date,
                is_active=True
            )

            try:
                print(f"\nINFO: Starting automatic setup for new company '{company.name}' (ID: {company.id})...")
                print(f"  -> Seeding Chart of Accounts for company {company.id}...")
                call_command('seed_coa', company.id)
                print(f"  -> Creating default transaction categories for company {company.id}...")
                call_command('create_default_categories', company_id=company.id)
                print(f"SUCCESS: Automatic setup for company {company.id} complete.\n")
            except Exception as e:
                print(f"ERROR: Automatic data seeding failed for company {company.id}: {e}")
                admin_note_suffix += "\nWARNING: Automatic data seeding failed. Please run manually."

        # Send Welcome Email (The context automatically uses the new username)
        send_email(
            subject=f"Welcome to WJ Accounting System!",
            template_name='emails/welcome_new_admin.html',
            context={
                'company_name': company.name,
                'contact_name': instance.contact_name,
                'username': admin_user.username, # This will be the new username
                'password': temp_password,
                'login_url': getattr(settings, 'APP_LOGIN_URL', 'http://127.0.0.1:8001/accounts/login/'),
                'plan_name': subscription.get_plan_display(),
                'expires_on': subscription.expires_on,
            },
            to_emails=[admin_user.email]
        )

        instance.verified_at = timezone.now()
        instance.admin_notes = f"{admin_note_suffix} Company '{company.name}' and admin user '{admin_user.username}' created."
        instance.save(update_fields=['verified_at', 'admin_notes'])

