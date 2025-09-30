# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\backup\tasks.py

from django.utils import timezone
from django.core.files import File

# Import your models and new utilities
from .models import Backup, BackupSettings
from apps.core.models import Company
from apps.authentication.models import User
from apps.reporting.utils import export_all_data_to_zip, export_audit_documents_to_zip
from apps.core.email_utils import send_email

def perform_backup_and_notify(company_id):
    """
    Enhanced backup with date range and incremental support.
    """
    try:
        company = Company.objects.get(id=company_id)
        settings = company.backup_settings
        
        # Determine backup parameters
        start_date = None
        end_date = None
        incremental = False
        last_backup_date = None
        
        if settings.backup_date_range_enabled:
            start_date = settings.backup_start_date
            end_date = settings.backup_end_date
        
        if settings.incremental_backup_enabled:
            incremental = True
            last_successful_backup = company.backups.filter(
                status=Backup.StatusChoices.SUCCESS
            ).first()
            if last_successful_backup:
                last_backup_date = last_successful_backup.created_at.date()
        
        print(f"Starting backup for {company.name}...")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Incremental: {incremental}")
        
        # Create backup record
        new_backup = Backup.objects.create(company=company, status=Backup.StatusChoices.IN_PROGRESS)
        
        # Generate backup with parameters
        path_to_zip_file = export_all_data_to_zip(
            company, 
            start_date=start_date, 
            end_date=end_date,
            incremental=incremental,
            last_backup_date=last_backup_date
        )
        
        # Save file and continue with email sending...
        with open(path_to_zip_file, 'rb') as f:
            filename = f'backup_{timezone.now().strftime("%Y%m%d_%H%M%S")}.zip'
            new_backup.file.save(filename, File(f))
        
        new_backup.status = Backup.StatusChoices.SUCCESS
        new_backup.notes = f"Backup type: {'Incremental' if incremental else 'Full'}, Date range: {start_date or 'All'} to {end_date or 'Current'}"
        new_backup.save()

        # 5. Email the file to ALL registered recipients
        recipients = [recipient.email for recipient in settings.recipients.all() if recipient.email]
        
        # Add company email as CC if it exists and not already in recipients
        cc_emails = []
        if company.email and company.email not in recipients:
            cc_emails.append(company.email)
        
        if recipients:
            print(f"Sending backup to {len(recipients)} recipients: {', '.join(recipients)}")
            if cc_emails:
                print(f"CC recipients: {', '.join(cc_emails)}")
                
            success = send_email(
                subject=f"Data Backup for {company.name}",
                template_name='emails/backup_notification.html',
                context={
                    'company': company,  # Pass full company object
                    'company_name': company.name,
                    'backup_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'backup_file': new_backup.file.name,
                    'backup_size': f"{new_backup.file.size / (1024*1024):.1f} MB" if new_backup.file else "Unknown",
                    'recipient_count': len(recipients) + len(cc_emails)
                },
                to_emails=recipients,
                cc_emails=cc_emails,  # Add CC functionality
                attachment_path=new_backup.file.path,
                company=company
            )
            
            if not success:
                print(f"Failed to send backup email for {company.name}")
                new_backup.notes = "Backup created but email sending failed"
                new_backup.save()
        else:
            print(f"No email recipients configured for {company.name}")
            new_backup.notes = "Backup created but no email recipients configured"
            new_backup.save()
        
        print(f"Successfully completed backup for {company.name}.")
        return True

    except Exception as e:
        print(f"Backup failed for company ID {company_id}: {e}")
        # If a 'new_backup' object was created, update its status to FAILED
        if 'new_backup' in locals():
            new_backup.status = Backup.StatusChoices.FAILED
            new_backup.notes = str(e)
            new_backup.save()
        return False

def send_audit_reminders(company_id):
    """
    Sends an email reminder to the auditor company about the user company.
    UPDATED: Separate TO and CC recipients, includes user company email in CC.
    """
    try:
        user_company = Company.objects.get(id=company_id)
        
        # Get the auditor company (separate from user company)
        auditor_company = Company.objects.filter(company_type=Company.CompanyType.AUDITOR).first()
        
        if not auditor_company:
            print(f"No auditor company found. Please configure auditor information.")
            return False
        
        # PRIMARY RECIPIENTS (TO): Look for auditors in the AUDITOR company
        auditors = User.objects.filter(
            company=auditor_company, 
            user_type=User.UserType.AUDITOR, 
            is_active=True
        )
        
        to_emails = [auditor.email for auditor in auditors if auditor.email]
        
                # If no auditor users found, use the auditor company's email as primary recipient
        if not to_emails and auditor_company.email:
            to_emails = [auditor_company.email]
        
        # CC RECIPIENTS: Always include user company email and any admin users
        cc_emails = []
        
        # Add user company email to CC
        if user_company.email:
            cc_emails.append(user_company.email)
        
        # Add user company admin users to CC
        admin_users = User.objects.filter(
            company=user_company,
            user_type=User.UserType.ADMIN,
            is_active=True
        )
        for admin in admin_users:
            if admin.email and admin.email not in cc_emails:
                cc_emails.append(admin.email)
        
        # Remove duplicates between TO and CC
        cc_emails = [email for email in cc_emails if email not in to_emails]
        
        if not to_emails:
            print(f"No primary recipients found for audit reminder. Cannot send reminder.")
            return False

        send_email(
            subject=f"Audit Reminder: {user_company.name}",
            template_name='emails/audit_reminder.html',
            context={
                'company': user_company,  # The company being audited
                'company_name': user_company.name,
                'auditor_company': auditor_company,  # The auditing firm
                'reminder_type': 'Quarterly Financial Review',
                'due_date': timezone.now() + timezone.timedelta(days=30),
                'days_until_due': 30,
                'period_end_date': timezone.now().strftime('%B %d, %Y'),
                'additional_info': {
                    'Company Phone': user_company.phone or 'Not provided',
                    'Company Email': user_company.email or 'Not provided',
                    'Registration Number': user_company.registration_number or 'Not provided',
                    'Industry': user_company.industry or 'Not specified',
                    'Tax Number': user_company.tax_number or 'Not provided',
                    'Address': user_company.address or 'Not provided',
                    'Website': user_company.website or 'Not provided'
                }
            },
            to_emails=to_emails,
            cc_emails=cc_emails,  # Add CC functionality
            company=user_company
        )
        
        print(f"Successfully sent audit reminders for {user_company.name}")
        print(f"TO: {', '.join(to_emails)}")
        if cc_emails:
            print(f"CC: {', '.join(cc_emails)}")
        
        return True

    except Exception as e:
        print(f"Failed to send audit reminders for company ID {company_id}: {e}")
        return False

def send_audit_documents(company_id):
    """
    NEW FUNCTION: Sends comprehensive audit documents package to auditors.
    Creates a zip file with all financial reports in multiple formats (CSV, Excel, PDF).
    """
    try:
        user_company = Company.objects.get(id=company_id)
        
        # Get the auditor company
        auditor_company = Company.objects.filter(company_type=Company.CompanyType.AUDITOR).first()
        
        if not auditor_company:
            print(f"No auditor company found. Please configure auditor information.")
            return False
        
        print(f"Preparing audit documents package for {user_company.name}...")
        
        # Generate comprehensive audit package
        audit_zip_path = export_audit_documents_to_zip(user_company)
        
        # PRIMARY RECIPIENTS (TO): Auditors
        auditors = User.objects.filter(
            company=auditor_company, 
            user_type=User.UserType.AUDITOR, 
            is_active=True
        )
        
        to_emails = [auditor.email for auditor in auditors if auditor.email]
        
        # If no auditor users found, use the auditor company's email
        if not to_emails and auditor_company.email:
            to_emails = [auditor_company.email]
        
        # CC RECIPIENTS: User company contacts
        cc_emails = []
        if user_company.email:
            cc_emails.append(user_company.email)
        
        # Add user company admin users to CC
        admin_users = User.objects.filter(
            company=user_company,
            user_type=User.UserType.ADMIN,
            is_active=True
        )
        for admin in admin_users:
            if admin.email and admin.email not in cc_emails:
                cc_emails.append(admin.email)
        
        # Remove duplicates between TO and CC
        cc_emails = [email for email in cc_emails if email not in to_emails]
        
        if not to_emails:
            print(f"No auditor recipients found for audit documents.")
            return False
        
        # Calculate file size
        import os
        file_size_mb = os.path.getsize(audit_zip_path) / (1024 * 1024)
        
        success = send_email(
            subject=f"Audit Documents Package: {user_company.name}",
            template_name='emails/audit_documents.html',
            context={
                'company': user_company,
                'company_name': user_company.name,
                'auditor_company': auditor_company,
                'audit_period': f"As of {timezone.now().strftime('%B %d, %Y')}",
                'package_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'file_size': f"{file_size_mb:.1f} MB",
                'included_reports': [
                    'Trial Balance (CSV)',
                    'Income Statement (CSV)', 
                    'Balance Sheet (CSV)',
                    'General Ledger (CSV)',
                    'Customer/Vendor List (CSV)',
                    'Inventory Items (CSV)',
                    'Assets Register (CSV)',
                    'Company Information (CSV)'
                ],
                'additional_info': {
                    'Company Phone': user_company.phone or 'Not provided',
                    'Company Email': user_company.email or 'Not provided',
                    'Registration Number': user_company.registration_number or 'Not provided',
                    'Industry': user_company.industry or 'Not specified',
                    'Tax Number': user_company.tax_number or 'Not provided',
                    'Address': user_company.address or 'Not provided',
                    'Website': user_company.website or 'Not provided',
                    'Currency': user_company.get_currency_display(),
                    'Fiscal Year Start': user_company.fiscal_year_start or 'Not set'
                }
            },
            to_emails=to_emails,
            cc_emails=cc_emails,
            attachment_path=audit_zip_path,
            company=user_company
        )
        
        if success:
            print(f"Successfully sent audit documents for {user_company.name}")
            print(f"TO: {', '.join(to_emails)}")
            if cc_emails:
                print(f"CC: {', '.join(cc_emails)}")
            print(f"Package size: {file_size_mb:.1f} MB")
        else:
            print(f"Failed to send audit documents for {user_company.name}")
        
        # Clean up temporary file
        try:
            os.remove(audit_zip_path)
        except:
            pass
        
        return success

    except Exception as e:
        print(f"Failed to send audit documents for company ID {company_id}: {e}")
        return False
