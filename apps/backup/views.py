# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\backup\views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import BackupSettings, Backup
from .forms import BackupSettingsForm, RecipientFormSet
from apps.core.forms import CompanyCurrencyForm
from apps.core.models import EmailConfiguration
from apps.authentication.decorators import user_type_required
from apps.authentication.models import User

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def backup_settings_view(request):
    user_company = request.user.company
    settings, created = BackupSettings.objects.get_or_create(company=user_company)
    
    # Get email configuration for status display only
    email_config = EmailConfiguration.objects.filter(company=user_company).first()

    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'backup_settings')
        
        if form_type == 'currency_settings':
            # Handle currency form
            form = BackupSettingsForm(instance=settings)
            formset = RecipientFormSet(instance=settings)
            currency_form = CompanyCurrencyForm(request.POST, instance=user_company)
            
            if currency_form.is_valid():
                currency_form.save()
                messages.success(request, "Currency settings updated successfully.")
                return redirect('backup:settings')
            else:
                messages.error(request, "Please correct the errors in the currency form.")
        
        else:
            # Handle backup settings (default)
            form = BackupSettingsForm(request.POST, instance=settings)
            formset = RecipientFormSet(request.POST, instance=settings)
            currency_form = CompanyCurrencyForm(instance=user_company)

            if form.is_valid() and formset.is_valid():
                with transaction.atomic():
                    form.save()
                    formset.save()
                
                messages.success(request, "Backup settings have been updated successfully.")
                return redirect('backup:settings')
            else:
                messages.error(request, "Please correct the errors below.")
    else:
        form = BackupSettingsForm(instance=settings)
        formset = RecipientFormSet(instance=settings)
        currency_form = CompanyCurrencyForm(instance=user_company)

    context = {
        'form': form,
        'formset': formset,
        'currency_form': currency_form,
        'email_config': email_config,  # For status display only
        'page_title': 'Backup Settings'
    }
    return render(request, 'backup/settings.html', context)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN])
def backup_history_view(request):
    user_company = request.user.company
    backup_history = Backup.objects.filter(company=user_company).order_by('-created_at')

    context = {
        'backup_history': backup_history,
        'page_title': 'Backup History'
    }
    return render(request, 'backup/history.html', context)