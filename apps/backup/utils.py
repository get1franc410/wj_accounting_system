# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\backup\utils.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from django.conf import settings

def send_backup_email(company, backup_file_path, recipients):
    """Send backup file as email attachment"""
    email_config = company.email_config
    
    if not email_config or not email_config.is_active:
        raise Exception("Email configuration not found or inactive")
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = email_config.email_address
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = f"Backup for {company.name} - {backup_file_path.split('/')[-1]}"
    
    # Email body
    body = f"""
    Dear Team,
    
    Please find attached the backup file for {company.name}.
    
    Backup Details:
    - Company: {company.name}
    - Date: {backup_file_path.split('/')[-1]}
    - File Size: {os.path.getsize(backup_file_path) / 1024:.2f} KB
    
    Best regards,
    Accounting System
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach backup file
    with open(backup_file_path, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    
    encoders.encode_base64(part)
    part.add_header(
        'Content-Disposition',
        f'attachment; filename= {os.path.basename(backup_file_path)}'
    )
    
    msg.attach(part)
    
    # Send email
    server = smtplib.SMTP(email_config.smtp_server, email_config.smtp_port)
    server.starttls()
    server.login(email_config.email_address, email_config.get_password())
    text = msg.as_string()
    server.sendmail(email_config.email_address, recipients, text)
    server.quit()
