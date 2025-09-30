# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\email_utils.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from django.template.loader import render_to_string
from django.conf import settings
from .models import EmailConfiguration

def send_email(subject, template_name, context, to_emails, cc_emails=None, from_email=None, attachment_path=None, company=None):
    """
    Sends an email with intelligent sender logic.
    - If 'company' is provided, it uses that company's specific email configuration.
    - If 'company' is NOT provided, it uses the system's default email settings from settings.py.
    """
    # --- KEY FIX: Start with system defaults from settings.py ---
    sender_email = settings.EMAIL_HOST_USER
    sender_password = settings.EMAIL_HOST_PASSWORD

    # --- NEW LOGIC: If a company is specified, try to use its config instead ---
    if company:
        try:
            email_config = company.email_config
            if email_config and email_config.is_active and email_config.email_address and email_config.app_password:
                sender_email = email_config.email_address
                sender_password = email_config.app_password
                print(f"INFO: Using specific email configuration for company: {company.name}")
        except EmailConfiguration.DoesNotExist:
            print(f"INFO: No specific email config for {company.name}. Falling back to system default.")
    else:
        print("INFO: No company provided. Using system default email configuration.")

    # Final check to ensure credentials are set from either source
    if not sender_email or not sender_password:
        print("ERROR: Email credentials are not configured. Email not sent. Please set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in settings.py.")
        return False

    try:
        # Render the email template
        html_content = render_to_string(template_name, context)
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        
        if isinstance(to_emails, str):
            to_emails = [to_emails]
        msg['To'] = ', '.join(to_emails)
        
        all_recipients = list(to_emails)
        if cc_emails:
            if isinstance(cc_emails, str):
                cc_emails = [cc_emails]
            cc_emails = [email.strip() for email in cc_emails if email.strip() and email.strip() not in to_emails]
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
                all_recipients.extend(cc_emails)
        
        msg['Subject'] = subject
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(attachment_path)}'
            )
            msg.attach(part)
        
        # Send email using SMTP
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        if settings.EMAIL_USE_TLS:
            server.starttls()
        
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, all_recipients, msg.as_string())
        server.quit()
        
        print(f"SUCCESS: Email sent from '{sender_email}' to '{', '.join(to_emails)}'")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to send email. Reason: {e}")
        return False

def send_email_simple(subject, message, to_emails, cc_emails=None, company=None):
    """
    Simple email sender without template, with CC support and smart sender logic.
    """
    sender_email = settings.EMAIL_HOST_USER
    sender_password = settings.EMAIL_HOST_PASSWORD

    if company:
        try:
            email_config = company.email_config
            if email_config and email_config.is_active and email_config.email_address and email_config.app_password:
                sender_email = email_config.email_address
                sender_password = email_config.app_password
        except EmailConfiguration.DoesNotExist:
            pass

    if not sender_email or not sender_password:
        print("ERROR: Email credentials are not configured. Email not sent.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        
        if isinstance(to_emails, str):
            to_emails = [to_emails]
        msg['To'] = ', '.join(to_emails)
        
        all_recipients = list(to_emails)
        if cc_emails:
            if isinstance(cc_emails, str):
                cc_emails = [cc_emails]
            cc_emails = [email.strip() for email in cc_emails if email.strip() and email.strip() not in to_emails]
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
                all_recipients.extend(cc_emails)
        
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))
        
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        if settings.EMAIL_USE_TLS:
            server.starttls()
        
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, all_recipients, msg.as_string())
        server.quit()
        
        return True
        
    except Exception as e:
        print(f"Error sending simple email: {e}")
        return False
