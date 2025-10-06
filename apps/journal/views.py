# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\journal\views.py

from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, DetailView, DeleteView
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db.models import Q, Avg, Count, Sum
from django.core.paginator import Paginator
from datetime import date
from apps.reporting.export_utils import export_to_csv, export_to_excel, export_to_pdf
from .models import JournalEntry
from .forms import JournalEntryForm, JournalEntryLineFormSet
from apps.core.models import Company
from apps.accounts.models import Account
from apps.authentication.decorators import RoleRequiredMixin
from apps.authentication.models import User

class JournalEntryListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'journal/journal_entry_list.html'
    context_object_name = 'journal_entries'
    ordering = ['-date']
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.AUDITOR, User.UserType.VIEWER]
    paginate_by = 20

    def get_queryset(self):
        queryset = JournalEntry.objects.filter(company=self.request.user.company).prefetch_related('lines__account')
        
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(description__icontains=search_query) |
                Q(lines__account__name__icontains=search_query) |
                Q(lines__account__account_number__icontains=search_query)
            ).distinct()
        
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
            
        return queryset.order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        # --- ACTION: REVISED SUMMARY STATISTICS LOGIC ---
        # The full (unpaginated) queryset is available from the view's object_list attribute
        filtered_entries = self.get_queryset()

        # Default values
        entries_this_month = 0
        average_lines = 0

        if filtered_entries.exists():
            current_month = timezone.now().date().replace(day=1)
            entries_this_month = filtered_entries.filter(date__gte=current_month).count()

            avg_agg = filtered_entries.annotate(
                num_lines=Count('lines')
            ).filter(num_lines__gt=0).aggregate(
                avg_val=Avg('num_lines')
            )
            
            if avg_agg.get('avg_val'):
                average_lines = round(avg_agg['avg_val'], 1)

        context['entries_this_month'] = entries_this_month
        context['average_lines'] = average_lines
        # The total count is already available in the template via `paginator.count`
        
        return context

class JournalEntryCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'journal/journal_entry_form.html'
    success_url = reverse_lazy('journal:journal-entry-list')
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT]

    def get_context_data(self, **kwargs):
        # ... (this method is unchanged)
        data = super().get_context_data(**kwargs)
        company = self.request.user.company
        
        if self.request.POST:
            data['lines'] = JournalEntryLineFormSet(self.request.POST, instance=self.object)
        else:
            data['lines'] = JournalEntryLineFormSet(instance=self.object)
        
        for form in data['lines']:
            if company:
                form.fields['account'].queryset = Account.objects.filter(
                    company=company, is_active=True
                ).order_by('account_number')
            else:
                form.fields['account'].queryset = Account.objects.none()

        return data


    def form_valid(self, form):
        context = self.get_context_data()
        lines = context['lines']
        
        with transaction.atomic():
            company = self.request.user.company
            if not company:
                messages.error(self.request, "Could not identify your company. Please log in again.")
                return self.form_invalid(form)

            transaction_date = form.cleaned_data.get('date')
            if company.is_period_closed_for_user(transaction_date, self.request.user):
                messages.error(
                    self.request,
                    f"The financial period for {transaction_date.strftime('%B %Y')} is closed. "
                    f"Only an Administrator can post entries to this period."
                )
                return self.form_invalid(form)

            form.instance.company = company
            form.instance.created_by = self.request.user
            self.object = form.save()

            if lines.is_valid():
                total_debits = Decimal('0.00')
                total_credits = Decimal('0.00')
                valid_lines = 0
                
                for line_form in lines:
                    if line_form.cleaned_data and not line_form.cleaned_data.get('DELETE', False):
                        debit = line_form.cleaned_data.get('debit') or Decimal('0.00')
                        credit = line_form.cleaned_data.get('credit') or Decimal('0.00')
                        
                        if debit > 0 and credit > 0:
                            messages.error(self.request, "A line cannot have both debit and credit amounts.")
                            return self.form_invalid(form)
                        
                        if debit == 0 and credit == 0:
                            messages.error(self.request, "Each line must have either a debit or credit amount.")
                            return self.form_invalid(form)
                        
                        total_debits += debit
                        total_credits += credit
                        valid_lines += 1

                if valid_lines < 2:
                    messages.error(self.request, "A journal entry must have at least 2 lines.")
                    return self.form_invalid(form)

                if total_debits != total_credits:
                    messages.error(self.request, f"Transaction is unbalanced. Debits ({total_debits}) do not equal Credits ({total_credits}).")
                    return self.form_invalid(form)
                
                if total_debits == 0:
                    messages.error(self.request, "A journal entry cannot have a zero balance.")
                    return self.form_invalid(form)

                lines.instance = self.object
                lines.save()
                
                try:
                    self.object.validate_balance()
                except ValidationError as e:
                    messages.error(self.request, f"Journal entry validation failed: {e}")
                    return self.form_invalid(form)
                    
            else:
                messages.error(self.request, "Please correct the errors in the entry lines below.")
                return self.form_invalid(form)

        messages.success(self.request, "Journal entry created successfully.")
        return super().form_valid(form)

class JournalEntryDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = JournalEntry
    template_name = 'journal/journal_entry_detail.html'
    context_object_name = 'journal_entry'
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.AUDITOR, User.UserType.VIEWER]

    def get_queryset(self):
        return JournalEntry.objects.filter(company=self.request.user.company)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        journal_entry = self.get_object()

        totals = journal_entry.lines.aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )

        context['total_debits'] = totals.get('total_debit') or Decimal('0.00')
        context['total_credits'] = totals.get('total_credit') or Decimal('0.00')

        return context
    
class JournalEntryDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = JournalEntry
    success_url = reverse_lazy('journal:journal-entry-list')
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT]
    
    def get_queryset(self):
        return JournalEntry.objects.filter(company=self.request.user.company)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Journal entry deleted successfully.")
        return super().delete(request, *args, **kwargs)
    
def export_journal_entries(request):
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    journal_entries = JournalEntry.objects.filter(company=company).order_by('-date')
    
    headers = ['Entry ID', 'Date', 'Description', 'Account', 'Debit', 'Credit']
    data = []
    
    for entry in journal_entries:
        first_line = True
        for line in entry.lines.all():
            data.append([
                f"JE-{entry.id}" if first_line else '',
                entry.date if first_line else '',
                entry.description if first_line else '',
                f"{line.account.account_number} - {line.account.name}",
                line.debit if line.debit > 0 else '',
                line.credit if line.credit > 0 else ''
            ])
            first_line = False
        data.append(['', '', '', '', '', ''])
    
    filename = f"journal_entries_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Journal Entries"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Journal Entries", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)