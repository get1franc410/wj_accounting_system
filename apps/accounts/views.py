# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\accounts\views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from apps.reporting.export_utils import export_to_csv, export_to_excel, export_to_pdf
from datetime import date
from django.utils.decorators import method_decorator
from decimal import Decimal
from apps.authentication.decorators import user_type_required, RoleRequiredMixin
from apps.authentication.models import User
from apps.journal.models import JournalEntryLine
from apps.accounts.models import Account, AccountType
from apps.accounts.forms import AccountForm

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def chart_of_accounts_list(request):
    """
    Displays the company's Chart of Accounts, grouped by account type,
    including balances for each account and totals for each group.
    """
    company = request.user.company
    grouped_accounts = {}
    account_types = AccountType.objects.all()

    for acc_type in account_types:
        accounts_in_group = Account.objects.filter(
            company=company, 
            account_type=acc_type
        ).order_by('account_number')
        
        if accounts_in_group.exists():
            group_total = Decimal('0.00')
            
            # Calculate the balance for each account and attach it to the object
            for account in accounts_in_group:
                account.balance = account.get_balance()
                
                # To get the group total, we only sum the balances of top-level accounts
                # (where parent is None). This avoids double-counting, as the balance of a 
                # parent account already includes the balances of its children.
                if account.parent is None:
                    group_total += account.balance

            # Store the list of accounts (with balances) and the calculated total for the group
            grouped_accounts[acc_type.name] = {
                'accounts': accounts_in_group,
                'total': group_total
            }

    context = {
        'grouped_accounts': grouped_accounts,
        'page_title': 'Chart of Accounts'
    }
    return render(request, 'accounts/chart_of_accounts_list.html', context)


@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN]), name='dispatch')
class AccountCreateView(LoginRequiredMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'accounts/account_form.html'
    success_url = reverse_lazy('accounts:chart-of-accounts')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        messages.success(self.request, "Account created successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create New Account'
        return context

@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN]), name='dispatch')
class AccountUpdateView(LoginRequiredMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = 'accounts/account_form.html'
    success_url = reverse_lazy('accounts:chart-of-accounts')

    def get_queryset(self):
        return Account.objects.filter(company=self.request.user.company)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Account updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit Account: {self.object.name}'
        return context

@method_decorator(user_type_required(allowed_roles=[User.UserType.ADMIN]), name='dispatch')
class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = Account
    template_name = 'accounts/account_confirm_delete.html'
    success_url = reverse_lazy('accounts:chart-of-accounts')

    def get_queryset(self):
        return Account.objects.filter(company=self.request.user.company)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Account '{self.object.name}' has been deleted.")
        return response

def export_chart_of_accounts(request):
    """Export chart of accounts in requested format"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    accounts = Account.objects.filter(company=company).order_by('account_number')
    
    headers = ['Account Number', 'Account Name', 'Account Type', 'Category', 'Current Balance', 'Is Active']
    data = []
    
    for account in accounts:
        data.append([
            account.account_number,
            account.name,
            account.account_type.name,
            account.account_type.get_category_display(),
            account.get_balance(),
            'Yes' if account.is_active else 'No'
        ])
    
    filename = f"chart_of_accounts_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Chart of Accounts"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Chart of Accounts", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)

def export_account_transactions(request, pk):
    """Export transactions for a specific account"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    account = get_object_or_404(Account, pk=pk, company=company)
    
    transactions = JournalEntryLine.objects.filter(account=account).order_by('-journal_entry__date')
    
    headers = ['Date', 'Journal Entry', 'Description', 'Debit', 'Credit', 'Running Balance']
    data = []
    
    # Account header
    data.append([f"Account: {account.account_number} - {account.name}", '', '', '', '', ''])
    data.append(['Account Type:', account.account_type.name, '', '', '', ''])
    data.append(['', '', '', '', '', ''])
    
    running_balance = 0
    is_credit_balance_account = account.account_type.category in [
        AccountType.Category.LIABILITY, 
        AccountType.Category.EQUITY, 
        AccountType.Category.REVENUE
    ]
    
    for transaction in transactions:
        if is_credit_balance_account:
            running_balance += (transaction.credit - transaction.debit)
        else:
            running_balance += (transaction.debit - transaction.credit)
        
        data.append([
            transaction.journal_entry.date,
            f"JE-{transaction.journal_entry.id}",
            transaction.journal_entry.description,
            transaction.debit if transaction.debit > 0 else '',
            transaction.credit if transaction.credit > 0 else '',
            running_balance
        ])
    
    filename = f"account_transactions_{account.account_number}_{date.today()}"
    title = f"Account Transactions - {account.name}"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Account Transactions", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)
    

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT])
def debug_account_balance(request, pk):
    """Debug account balance calculation"""
    company = request.user.company
    account = get_object_or_404(Account, pk=pk, company=company)
    
    # Get all journal lines for this account
    lines = account.journal_lines.all().order_by('journal_entry__date')
    
    running_balance = Decimal('0.00')
    line_details = []
    
    for line in lines:
        if account.account_type.category in [AccountType.Category.ASSET, AccountType.Category.EXPENSE]:
            running_balance += (line.debit - line.credit)
        else:
            running_balance += (line.credit - line.debit)
        
        line_details.append({
            'date': line.journal_entry.date,
            'description': line.journal_entry.description,
            'debit': line.debit,
            'credit': line.credit,
            'running_balance': running_balance
        })
    
    context = {
        'account': account,
        'line_details': line_details,
        'final_balance': running_balance,
        'calculated_balance': account.get_balance()
    }
    
    return render(request, 'accounts/debug_balance.html', context)