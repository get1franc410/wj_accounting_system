# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\transactions\views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.db.models import Q, F
from django.core.paginator import Paginator
from apps.reporting.export_utils import export_to_csv, export_to_excel, export_to_pdf
from datetime import date
from django.utils import timezone
from decimal import Decimal
from django.utils.decorators import method_decorator
from apps.authentication.decorators import RoleRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.authentication.models import User

from .models import Transaction, TransactionItem
from .forms import TransactionForm, TransactionItemFormSet
from .services import create_journal_entry_for_transaction
from apps.customers.models import Customer
from apps.accounts.models import Account, AccountType
from .constants import TransactionType

from .models import TransactionCategory  # ADD THIS
from .forms import TransactionCategoryForm  # ADD THIS


def is_admin_user(user):
    """Check if user is admin/staff"""
    return user.is_staff or user.is_superuser

class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin access"""
    def test_func(self):
        return is_admin_user(self.request.user)
    
class TransactionCategoryListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = TransactionCategory
    template_name = 'transactions/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return TransactionCategory.objects.filter(
            company=self.request.user.company
        ).select_related('account_type', 'default_account').order_by('name')

class TransactionCategoryCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = TransactionCategory
    form_class = TransactionCategoryForm
    template_name = 'transactions/category_form.html'
    success_url = reverse_lazy('transactions:category_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs
    
    def form_valid(self, form):
        form.instance.company = self.request.user.company
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create Transaction Category'
        return context

class TransactionCategoryUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = TransactionCategory
    form_class = TransactionCategoryForm
    template_name = 'transactions/category_form.html'
    success_url = reverse_lazy('transactions:category_list')
    
    def get_queryset(self):
        return TransactionCategory.objects.filter(company=self.request.user.company)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit {self.object.name}'
        return context

class TransactionCategoryDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = TransactionCategory
    template_name = 'transactions/category_detail.html'
    context_object_name = 'category'
    
    def get_queryset(self):
        return TransactionCategory.objects.filter(company=self.request.user.company)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate usage statistics
        now = timezone.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        context['monthly_count'] = self.object.transactions.filter(
            date__gte=first_day_of_month.date()
        ).count()
        
        last_transaction = self.object.transactions.order_by('-date').first()
        context['last_used'] = last_transaction.date if last_transaction else None
        
        return context

class TransactionListView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER]
    
    def get(self, request):
        company = request.user.company
        transactions = Transaction.objects.filter(company=company).order_by('-date')
        
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            transactions = transactions.filter(
                Q(reference_number__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(customer__name__icontains=search_query)
            )
        
        # Filter by transaction type
        transaction_type = request.GET.get('type', '')
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        # Filter by payment status
        payment_status = request.GET.get('status', '')
        if payment_status == 'paid':
            transactions = transactions.filter(amount_paid__gte=F('total_amount'))
        elif payment_status == 'unpaid':
            transactions = transactions.filter(amount_paid=0)
        elif payment_status == 'partial':
            transactions = transactions.filter(amount_paid__gt=0, amount_paid__lt=F('total_amount'))
        
        # Filter by customer
        customer_id = request.GET.get('customer', '')
        if customer_id:
            transactions = transactions.filter(customer_id=customer_id)
        
        # Date range filter
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        if date_from:
            transactions = transactions.filter(date__gte=date_from)
        if date_to:
            transactions = transactions.filter(date__lte=date_to)
        
        # Pagination
        paginator = Paginator(transactions, 25)  # 25 transactions per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get filter options
        customers = Customer.objects.filter(company=company).order_by('name')
        
        context = {
            'transactions': page_obj,
            'customers': customers,
            'search_query': search_query,
            'selected_type': transaction_type,
            'selected_status': payment_status,
            'selected_customer': customer_id,
            'date_from': date_from,
            'date_to': date_to,
            'page_title': 'Transactions'
        }
        return render(request, 'transactions/transaction_list.html', context)

# --- Transaction Detail View ---
class TransactionDetailView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER]
    def get(self, request, pk):
        company = request.user.company
        transaction_obj = get_object_or_404(Transaction, pk=pk, company=company)
        context = {
            'transaction': transaction_obj,
            'page_title': f'Details for Transaction #{transaction_obj.id}'
        }
        return render(request, 'transactions/transaction_detail.html', context)

class TransactionInvoiceView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    """
    Renders a printable invoice/receipt for a specific transaction.
    """
    model = Transaction
    template_name = 'transactions/transaction_invoice.html'
    context_object_name = 'transaction'
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER]

    def get_queryset(self):
        # Ensure users can only see invoices for their own company
        return Transaction.objects.filter(company=self.request.user.company)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Invoice for Transaction #{self.object.id}"
        return context
    
class TransactionCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT]
    template_name = 'transactions/transaction_form.html'

    def get(self, request):
        form = TransactionForm(company=request.user.company, user=request.user)
        formset = TransactionItemFormSet(
            queryset=TransactionItem.objects.none(),
            form_kwargs={'company': request.user.company}
        )
        context = {
            'form': form,
            'formset': formset,
            'page_title': 'Create New Transaction'
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = TransactionForm(request.POST, request.FILES, company=request.user.company, user=request.user)
        use_line_items = request.POST.get('use_line_items') == 'on'
        
        formset = TransactionItemFormSet(request.POST, form_kwargs={'company': request.user.company}) if use_line_items else TransactionItemFormSet(queryset=TransactionItem.objects.none())

        is_form_valid = form.is_valid()
        is_formset_valid = not use_line_items or formset.is_valid()

        if is_form_valid and is_formset_valid:
            try:
                with transaction.atomic():
                    transaction_obj = form.save(commit=False)
                    transaction_obj.company = request.user.company
                    transaction_obj.created_by = request.user

                    if use_line_items:
                        # --- THIS LOGIC IS CORRECT ---
                        # It iterates over cleaned_data, which only contains valid forms.
                        total = sum(
                            (item_data.get('quantity', 0) or 0) * (item_data.get('unit_price', 0) or 0)
                            for item_data in formset.cleaned_data if item_data and not item_data.get('DELETE')
                        )
                        transaction_obj.total_amount = total
                    else:
                        transaction_obj.total_amount = form.cleaned_data.get('manual_total_amount', Decimal('0.00'))

                    transaction_obj.save()

                    if use_line_items:
                        formset.instance = transaction_obj
                        formset.save() # This is now safe because formset is valid

                    create_journal_entry_for_transaction(transaction_obj)

                messages.success(request, "Transaction created successfully!")
                return redirect('transactions:transaction_detail', pk=transaction_obj.pk)
            except Exception as e:
                messages.error(request, f"An unexpected error occurred during save: {e}")
        
        context = {'form': form, 'formset': formset, 'page_title': 'Create New Transaction'}
        return render(request, self.template_name, context)
    
class TransactionUpdateView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT]
    template_name = 'transactions/transaction_form.html'

    def get(self, request, pk):
        transaction_obj = get_object_or_404(Transaction, pk=pk, company=request.user.company)
        form = TransactionForm(instance=transaction_obj, company=request.user.company, user=request.user)
        formset = TransactionItemFormSet(
            instance=transaction_obj,
            form_kwargs={'company': request.user.company}
        )
        context = {
            'form': form,
            'formset': formset,
            'transaction': transaction_obj,
            'page_title': f'Edit Transaction #{transaction_obj.id}'
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        transaction_obj = get_object_or_404(Transaction, pk=pk, company=request.user.company)
        form = TransactionForm(request.POST, request.FILES, instance=transaction_obj, company=request.user.company, user=request.user)
        use_line_items = request.POST.get('use_line_items') == 'on'

        formset = TransactionItemFormSet(
            request.POST, 
            instance=transaction_obj, 
            form_kwargs={'company': request.user.company}
        ) if use_line_items else TransactionItemFormSet(
            instance=transaction_obj, 
            queryset=TransactionItem.objects.none()
        )

        is_form_valid = form.is_valid()
        is_formset_valid = not use_line_items or formset.is_valid()

        if is_form_valid and is_formset_valid:
            try:
                with transaction.atomic():
                    updated_transaction = form.save(commit=False)
                    updated_transaction.updated_by = request.user  # ADD THIS LINE
                    
                    if use_line_items:
                        # Calculate total from valid formset data
                        total = sum(
                            (item_data.get('quantity', 0) or 0) * (item_data.get('unit_price', 0) or 0)
                            for item_data in formset.cleaned_data 
                            if item_data and not item_data.get('DELETE')
                        )
                        updated_transaction.total_amount = total
                    else:
                        updated_transaction.total_amount = form.cleaned_data.get('manual_total_amount', Decimal('0.00'))
                    
                    updated_transaction.save()

                    if use_line_items:
                        formset.save()
                    else:
                        # If not using line items, delete any existing ones
                        updated_transaction.items.all().delete()

                    create_journal_entry_for_transaction(updated_transaction)

                messages.success(request, "Transaction updated successfully!")
                return redirect('transactions:transaction_detail', pk=updated_transaction.pk)
            except Exception as e:
                messages.error(request, f"An error occurred during update: {e}")

        context = {
            'form': form, 
            'formset': formset, 
            'transaction': transaction_obj, 
            'page_title': f'Edit Transaction #{transaction_obj.id}'
        }
        return render(request, self.template_name, context)
        
class RecordPaymentView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT]
    template_name = 'transactions/record_payment.html'

    def get(self, request, pk):
        transaction_obj = get_object_or_404(Transaction, pk=pk, company=request.user.company)
        
        if transaction_obj.balance_due <= 0:
            messages.info(request, "This transaction is already fully paid.")
            return redirect('transactions:transaction_detail', pk=pk)
        
        context = {
            'transaction': transaction_obj,
            'page_title': f'Record Payment for Transaction #{transaction_obj.id}'
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        transaction_obj = get_object_or_404(Transaction, pk=pk, company=request.user.company)
        
        try:
            payment_amount = Decimal(request.POST.get('payment_amount', '0'))
            payment_date = request.POST.get('payment_date')
            payment_method = request.POST.get('payment_method')
            payment_reference = request.POST.get('payment_reference', '')
            
            # Validation
            if payment_amount <= 0:
                messages.error(request, "Payment amount must be greater than zero.")
                return redirect('transactions:record_payment', pk=pk)
            
            if payment_amount > transaction_obj.balance_due:
                messages.error(request, "Payment amount cannot exceed the balance due.")
                return redirect('transactions:record_payment', pk=pk)
            
            # Update transaction
            with transaction.atomic():
                transaction_obj.amount_paid += payment_amount
                transaction_obj.save()
                
                # Update customer balance
                if transaction_obj.customer:
                    transaction_obj.customer.update_balances()
            
            messages.success(request, f"Payment of {payment_amount} recorded successfully!")
            return redirect('transactions:transaction_detail', pk=pk)
            
        except (ValueError, TypeError) as e:
            messages.error(request, "Invalid payment amount entered.")
            return redirect('transactions:record_payment', pk=pk)
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('transactions:record_payment', pk=pk)


class TransactionDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Handles the attempt to delete a transaction.
    Instead of deleting, it informs the user that transactions cannot be deleted
    and advises them to create a correctional journal entry.
    """
    allowed_roles = [User.UserType.ADMIN, User.UserType.ACCOUNTANT]
    template_name = 'transactions/transaction_confirm_delete.html'

    def get(self, request, pk):
        transaction_obj = get_object_or_404(Transaction, pk=pk, company=request.user.company)
        
        messages.warning(request, "Deletion is not permitted to maintain a complete audit trail. Please see the explanation below.")

        context = {
            'transaction': transaction_obj,
            'page_title': 'Deletion Not Permitted'
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        # This function now handles the form submission from the old template.
        # It will not delete the object but will show a message and redirect.
        transaction_obj = get_object_or_404(Transaction, pk=pk, company=request.user.company)
        messages.error(
            request,
            "As per accounting best practices, transactions cannot be deleted. "
            "Please create a correctional journal entry to reverse any errors."
        )
        return redirect('transactions:transaction_detail', pk=transaction_obj.pk)

@require_GET
def accounts_by_type_api(request, account_type_id):
    """API endpoint to get accounts filtered by account type"""
    try:
        account_type = AccountType.objects.get(id=account_type_id)
        accounts = Account.objects.filter(
            company=request.user.company,
            account_type=account_type
        ).values('id', 'name', 'account_number').order_by('account_number')
        
        return JsonResponse({
            'accounts': list(accounts),
            'account_category': account_type.category,
            'account_type_name': account_type.name,
            'recommended_transaction_types': TransactionType.get_recommended_for_account_category(
                account_type.category
            )
        })
    except AccountType.DoesNotExist:
        return JsonResponse({'error': 'Account type not found'}, status=404)
    
def export_transactions(request):
    """Export transactions in requested format"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    transactions = Transaction.objects.filter(company=company).order_by('-date')
    
    headers = ['Date', 'Type', 'Customer/Vendor', 'Reference', 'Description', 'Total Amount', 'Amount Paid', 'Balance Due', 'Status']
    data = []
    
    for transaction in transactions:
        data.append([
            transaction.date,
            transaction.get_transaction_type_display(),
            transaction.customer.name if transaction.customer else '',
            transaction.reference_number or '',
            transaction.description or '',
            transaction.total_amount,
            transaction.amount_paid,
            transaction.balance_due,
            transaction.payment_status
        ])
    
    filename = f"transactions_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Transaction List"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Transactions", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)

def export_transaction_detail(request, pk):
    """Export individual transaction with line items"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    transaction = get_object_or_404(Transaction, pk=pk, company=company)
    
    headers = ['Item', 'Description', 'Quantity', 'Unit Price', 'Line Total']
    data = []
    
    # Transaction header
    data.append(['Transaction Details', '', '', '', ''])
    data.append(['Date:', transaction.date, '', '', ''])
    data.append(['Type:', transaction.get_transaction_type_display(), '', '', ''])
    data.append(['Customer/Vendor:', transaction.customer.name if transaction.customer else 'N/A', '', '', ''])
    data.append(['Reference:', transaction.reference_number or 'N/A', '', '', ''])
    data.append(['Description:', transaction.description or 'N/A', '', '', ''])
    data.append(['', '', '', '', ''])
    
    # Line items
    if transaction.items.exists():
        for item in transaction.items.all():
            data.append([
                item.item.name,
                item.description or item.item.description,
                item.quantity,
                item.unit_price,
                item.line_total
            ])
    else:
        data.append(['No line items', '', '', '', transaction.total_amount])
    
    # Summary
    data.append(['', '', '', '', ''])
    data.append(['', '', '', 'Subtotal:', transaction.subtotal])
    data.append(['', '', '', 'Tax:', transaction.tax_amount])
    data.append(['', '', '', 'Total:', transaction.total_amount])
    data.append(['', '', '', 'Amount Paid:', transaction.amount_paid])
    data.append(['', '', '', 'Balance Due:', transaction.balance_due])
    
    filename = f"transaction_detail_{transaction.id}_{date.today()}"
    title = f"Transaction Detail - {transaction.reference_number or transaction.id}"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Transaction Detail", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)