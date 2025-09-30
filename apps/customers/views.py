# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\customers\views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q, F
from django.core.paginator import Paginator
from django.db import transaction as db_transaction
from apps.reporting.export_utils import export_to_csv, export_to_excel, export_to_pdf
from datetime import date
from .models import Customer
from .forms import CustomerForm
from apps.accounts.models import Account
from apps.core.models import Company 
from decimal import Decimal
from apps.core.email_utils import send_email
from apps.authentication.decorators import user_type_required
from apps.authentication.models import User
from apps.transactions.models import Transaction
from apps.transactions.constants import TransactionType  # 🎯 IMPORT TRANSACTION TYPES
from apps.journal.models import JournalEntry, JournalEntryLine
from apps.core.utils import get_currency_symbol

def get_current_company(request):
    company = request.user.company
    if not company:
        messages.error(request, "CRITICAL: No active company found. Please contact support.")
        return None
    return company

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def customer_list(request):
    customers = Customer.objects.filter(company=request.user.company)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    # Filter by entity type
    entity_type = request.GET.get('type', '')
    if entity_type:
        customers = customers.filter(entity_type=entity_type)
    
    # Filter by balance status
    balance_filter = request.GET.get('balance_filter', '')
    if balance_filter == 'has_receivable':
        customers = customers.filter(receivable_balance__gt=0)
    elif balance_filter == 'has_payable':
        customers = customers.filter(payable_balance__gt=0)
    elif balance_filter == 'zero_balance':
        customers = customers.filter(receivable_balance=0, payable_balance=0)
    
    # Order by name
    customers = customers.order_by('name')
    
    # 🎯 CALCULATE REAL TOTALS BEFORE PAGINATION
    from django.db.models import Sum
    
    # Get totals from all customers (not just current page)
    all_customers = Customer.objects.filter(company=request.user.company)
    
    # Apply same filters to totals calculation
    if search_query:
        all_customers = all_customers.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    if entity_type:
        all_customers = all_customers.filter(entity_type=entity_type)
    
    if balance_filter == 'has_receivable':
        all_customers = all_customers.filter(receivable_balance__gt=0)
    elif balance_filter == 'has_payable':
        all_customers = all_customers.filter(payable_balance__gt=0)
    elif balance_filter == 'zero_balance':
        all_customers = all_customers.filter(receivable_balance=0, payable_balance=0)
    
    # 🎯 CALCULATE ACTUAL TOTALS
    totals = all_customers.aggregate(
        total_receivables=Sum('receivable_balance'),
        total_payables=Sum('payable_balance')
    )
    
    total_receivables = totals['total_receivables'] or Decimal('0.00')
    total_payables = totals['total_payables'] or Decimal('0.00')
    
    # Count customers with balances
    customers_with_receivables = all_customers.filter(receivable_balance__gt=0).count()
    customers_with_payables = all_customers.filter(payable_balance__gt=0).count()
    active_this_month = all_customers.count()  # You can refine this logic
    
    # Pagination
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'customers': page_obj,
        'search_query': search_query,
        'selected_type': entity_type,
        'selected_balance': balance_filter,
        # 🎯 ADD REAL TOTALS TO CONTEXT
        'total_receivables': total_receivables,
        'total_payables': total_payables,
        'customers_with_receivables': customers_with_receivables,
        'customers_with_payables': customers_with_payables,
        'active_this_month': active_this_month,
        'total_customers': all_customers.count(),
    }
    return render(request, 'customers/customer_list.html', context)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk, company=request.user.company)
    
    # 🎯 FIX: Get transactions and group payments with their parent transactions
    all_transactions = Transaction.objects.filter(customer=customer).order_by('-date', '-created_at')
    
    # Separate original transactions from payments
    original_transactions = []
    payment_transactions = {}
    
    for tx in all_transactions:
        if tx.transaction_type == TransactionType.PAYMENT:
            # Extract parent transaction ID from description or reference
            if "Transaction #" in tx.description:
                try:
                    parent_id = int(tx.description.split("Transaction #")[1].split()[0])
                    if parent_id not in payment_transactions:
                        payment_transactions[parent_id] = []
                    payment_transactions[parent_id].append(tx)
                except (ValueError, IndexError):
                    # If we can't parse parent ID, treat as standalone payment
                    original_transactions.append(tx)
            else:
                original_transactions.append(tx)
        else:
            original_transactions.append(tx)
    
    # Add payment info to original transactions
    for tx in original_transactions:
        tx.related_payments = payment_transactions.get(tx.id, [])
    
    context = {
        'customer': customer,
        'transaction_history': original_transactions
    }
    return render(request, 'customers/customer_detail.html', context)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT])
def customer_create(request):
    company = request.user.company
    if request.method == 'POST':
        form = CustomerForm(request.POST, company=company)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.company = company 
            entity_type = form.cleaned_data['entity_type']

            # Create A/R Ledger if needed
            if entity_type in [Customer.CUSTOMER, Customer.BOTH]:
                try:
                    # --- FIX: Use system_account for a robust lookup ---
                    ar_parent = Account.objects.get(company=company, system_account=Account.SystemAccount.ACCOUNTS_RECEIVABLE)
                    sub_ledger_count = Account.objects.filter(company=company, parent=ar_parent).count()
                    new_account_number = f"{ar_parent.account_number}-{sub_ledger_count + 1}"
                    customer.receivable_account = Account.objects.create(
                        company=company, name=f"{customer.name} (A/R)",
                        account_number=new_account_number, account_type=ar_parent.account_type, parent=ar_parent
                    )
                except Account.DoesNotExist:
                    messages.error(request, "Configuration Error: The main 'Accounts Receivable' system account was not found.")
                    return render(request, 'customers/customer_form.html', {'form': form})

            # Create A/P Ledger if needed
            if entity_type in [Customer.VENDOR, Customer.BOTH]:
                try:
                    # --- FIX: Use system_account for a robust lookup ---
                    ap_parent = Account.objects.get(company=company, system_account=Account.SystemAccount.ACCOUNTS_PAYABLE)
                    sub_ledger_count = Account.objects.filter(company=company, parent=ap_parent).count()
                    new_account_number = f"{ap_parent.account_number}-{sub_ledger_count + 1}"
                    customer.payable_account = Account.objects.create(
                        company=company, name=f"{customer.name} (A/P)",
                        account_number=new_account_number, account_type=ap_parent.account_type, parent=ap_parent
                    )
                except Account.DoesNotExist:
                    messages.error(request, "Configuration Error: The main 'Accounts Payable' system account was not found.")
                    return render(request, 'customers/customer_form.html', {'form': form})
            
            customer.save()
            messages.success(request, f"Successfully created {customer.name}.")
            return redirect('customers:customer-list')
    else:
        form = CustomerForm(company=company)

    return render(request, 'customers/customer_form.html', {'form': form})

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT])
def customer_update(request, pk):
    company = get_current_company(request)
    if not company: return redirect('customers:customer-list')
    customer = get_object_or_404(Customer, pk=pk, company=company)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer, company=company)
        if form.is_valid():
            updated_customer = form.save(commit=False)
            entity_type = form.cleaned_data['entity_type']

            # Cleanly handle entity type changes
            if entity_type == Customer.VENDOR and updated_customer.receivable_account:
                if updated_customer.receivable_balance == Decimal('0.00'):
                    updated_customer.receivable_account.delete()
                    updated_customer.receivable_account = None
                else:
                    messages.warning(request, "Could not remove A/R role. Customer has an outstanding receivable balance.")

            if entity_type == Customer.CUSTOMER and updated_customer.payable_account:
                if updated_customer.payable_balance == Decimal('0.00'):
                    updated_customer.payable_account.delete()
                    updated_customer.payable_account = None
                else:
                    messages.warning(request, "Could not remove Vendor role. Customer has an outstanding payable balance.")

            # Create accounts if they are needed and don't exist
            if entity_type in [Customer.CUSTOMER, Customer.BOTH] and not updated_customer.receivable_account:
                try:
                    # --- FIX: Use system_account for a robust lookup ---
                    ar_parent = Account.objects.get(company=company, system_account=Account.SystemAccount.ACCOUNTS_RECEIVABLE)
                    sub_ledger_count = Account.objects.filter(company=company, parent=ar_parent).count()
                    new_account_number = f"{ar_parent.account_number}-{sub_ledger_count + 1}"
                    updated_customer.receivable_account = Account.objects.create(
                        company=company, name=f"{updated_customer.name} (A/R)",
                        account_number=new_account_number, account_type=ar_parent.account_type, parent=ar_parent
                    )
                except Account.DoesNotExist:
                    messages.error(request, "Configuration Error: The main 'Accounts Receivable' system account not found.")
                    return render(request, 'customers/customer_form.html', {'form': form, 'is_edit': True})

            if entity_type in [Customer.VENDOR, Customer.BOTH] and not updated_customer.payable_account:
                try:
                    # --- FIX: Use system_account for a robust lookup ---
                    ap_parent = Account.objects.get(company=company, system_account=Account.SystemAccount.ACCOUNTS_PAYABLE)
                    sub_ledger_count = Account.objects.filter(company=company, parent=ap_parent).count()
                    new_account_number = f"{ap_parent.account_number}-{sub_ledger_count + 1}"
                    updated_customer.payable_account = Account.objects.create(
                        company=company, name=f"{updated_customer.name} (A/P)",
                        account_number=new_account_number, account_type=ap_parent.account_type, parent=ap_parent
                    )
                except Account.DoesNotExist:
                    messages.error(request, "Configuration Error: The main 'Accounts Payable' system account not found.")
                    return render(request, 'customers/customer_form.html', {'form': form, 'is_edit': True})
            
            updated_customer.save()
            messages.success(request, f"Successfully updated {updated_customer.name}.")
            return redirect('customers:customer-detail', pk=updated_customer.pk)
    else:
        form = CustomerForm(instance=customer, company=company)

    return render(request, 'customers/customer_form.html', {'form': form, 'customer': customer, 'is_edit': True})

def create_payment_journal_entry(transaction_obj, payment_amount):
    """
    Creates a journal entry for customer payment recording
    Debit: Cash/Bank Account (increase cash)
    Credit: Main Accounts Receivable Account (decrease total receivables)
    """
    try:
        with db_transaction.atomic():
            # Get the cash account (where payment is received)
            cash_account = Account.objects.get(
                company=transaction_obj.company,
                system_account=Account.SystemAccount.DEFAULT_CASH
            )
            
            # 🎯 FIX: Get the MAIN Accounts Receivable account, not the customer's individual account
            main_ar_account = Account.objects.get(
                company=transaction_obj.company,
                system_account=Account.SystemAccount.ACCOUNTS_RECEIVABLE
            )
            
            # Create the journal entry
            journal_entry = JournalEntry.objects.create(
                company=transaction_obj.company,
                date=timezone.now().date(),
                description=f"Payment received from {transaction_obj.customer.name} for Transaction #{transaction_obj.id}",
                created_by=None  # Will be set by the view if available
            )
            
            # Debit: Cash Account (increase cash)
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=cash_account,
                debit=payment_amount,
                credit=Decimal('0.00'),
                description=f"Payment from {transaction_obj.customer.name}"
            )
            
            # 🎯 FIX: Credit the MAIN Accounts Receivable account (decrease total receivables)
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=main_ar_account,  # ← Changed from receivable_account to main_ar_account
                debit=Decimal('0.00'),
                credit=payment_amount,
                description=f"Payment for Transaction #{transaction_obj.id} from {transaction_obj.customer.name}"
            )
            
            return journal_entry
            
    except Account.DoesNotExist:
        raise ValueError("Required accounts not found. Please check system account configuration.")
    except Exception as e:
        raise ValueError(f"Error creating payment journal entry: {str(e)}")
    
def create_vendor_payment_journal_entry(transaction_obj, payment_amount):
    """
    Creates a journal entry for vendor payment recording
    Debit: Main Accounts Payable Account (decrease total payables)
    Credit: Cash/Bank Account (decrease cash)
    """
    try:
        with db_transaction.atomic():
            # Get the cash account (where payment is made from)
            cash_account = Account.objects.get(
                company=transaction_obj.company,
                system_account=Account.SystemAccount.DEFAULT_CASH
            )
            
            # Get the MAIN Accounts Payable account
            main_ap_account = Account.objects.get(
                company=transaction_obj.company,
                system_account=Account.SystemAccount.ACCOUNTS_PAYABLE
            )
            
            # Create the journal entry
            journal_entry = JournalEntry.objects.create(
                company=transaction_obj.company,
                date=timezone.now().date(),
                description=f"Payment made to {transaction_obj.customer.name} for Transaction #{transaction_obj.id}",
                created_by=None  # Will be set by the view if available
            )
            
            # Debit: Main Accounts Payable (decrease what we owe)
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=main_ap_account,
                debit=payment_amount,
                credit=Decimal('0.00'),
                description=f"Payment to {transaction_obj.customer.name}"
            )
            
            # Credit: Cash Account (decrease cash)
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=cash_account,
                debit=Decimal('0.00'),
                credit=payment_amount,
                description=f"Payment for Transaction #{transaction_obj.id} to {transaction_obj.customer.name}"
            )
            
            return journal_entry
            
    except Account.DoesNotExist:
        raise ValueError("Required accounts not found. Please check system account configuration.")
    except Exception as e:
        raise ValueError(f"Error creating vendor payment journal entry: {str(e)}")
    
@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT])
def record_payment(request, pk):
    """Record payment for specific customer transaction"""
    customer = get_object_or_404(Customer, pk=pk, company=request.user.company)
    
    if request.method == 'POST':
        transaction_id = request.POST.get('transaction_id')
        amount = Decimal(request.POST.get('amount', '0'))
        payment_date = request.POST.get('payment_date')
        payment_notes = request.POST.get('notes', '')
        
        transaction_obj = get_object_or_404(
            Transaction, 
            id=transaction_id, 
            customer=customer,
            company=request.user.company
        )
        
        if amount <= 0:
            messages.error(request, "Payment amount must be greater than zero")
        elif amount > transaction_obj.balance_due:
            currency_symbol = get_currency_symbol(request.user.company.currency)
            messages.error(request, f"Payment amount cannot exceed balance due of {currency_symbol}{transaction_obj.balance_due}")
        else:
            try:
                with db_transaction.atomic():
                    # 🎯 FIX 1: Update the original transaction's amount_paid
                    transaction_obj.amount_paid += amount
                    transaction_obj.save()
                    
                    # 🎯 FIX 2: Create a payment transaction with proper reference
                    payment_transaction = Transaction.objects.create(
                        company=request.user.company,
                        customer=customer,
                        transaction_type=TransactionType.PAYMENT,
                        date=payment_date or timezone.now().date(),
                        description=f"Payment for Transaction #{transaction_obj.id}" + (f" - {payment_notes}" if payment_notes else ""),
                        reference_number=f"PAY-{transaction_obj.id}-{timezone.now().strftime('%Y%m%d%H%M')}",
                        total_amount=amount,
                        amount_paid=amount,  # Payment is fully "paid" immediately
                        created_by=request.user
                    )
                    
                    # 🎯 FIX 3: Update customer balances
                    customer.update_balances()
                    
                    # Create journal entry for payment
                    journal_entry = create_payment_journal_entry(transaction_obj, amount)
                    journal_entry.created_by = request.user
                    journal_entry.save()

                    currency_symbol = get_currency_symbol(request.user.company.currency)
                    messages.success(
                        request, 
                        f"Payment of {currency_symbol}{amount} recorded successfully for Transaction #{transaction_obj.id}"
                    )
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"An error occurred while recording payment: {str(e)}")
    
    return redirect('customers:customer-detail', pk=pk)


def create_transaction_journal_entry(transaction_obj):
    """
    Creates appropriate journal entries based on transaction type
    """
    try:
        with db_transaction.atomic():
            if transaction_obj.transaction_type == TransactionType.SALE:
                # Sales transaction
                # Debit: Individual Customer A/R
                # Credit: Sales Revenue
                pass  # Your existing sales logic
                
            elif transaction_obj.transaction_type in [TransactionType.PURCHASE, TransactionType.EXPENSE]:
                # Purchase/Bill transaction
                expense_account = Account.objects.get(
                    company=transaction_obj.company,
                    account_number='5000'  # Your expense account
                )
                
                main_ap_account = Account.objects.get(
                    company=transaction_obj.company,
                    system_account=Account.SystemAccount.ACCOUNTS_PAYABLE
                )
                
                journal_entry = JournalEntry.objects.create(
                    company=transaction_obj.company,
                    date=transaction_obj.date,
                    description=f"Purchase/Bill - Transaction #{transaction_obj.id}",
                    created_by=transaction_obj.created_by
                )
                
                # Debit: Expense Account
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=expense_account,
                    debit=transaction_obj.total_amount,
                    credit=Decimal('0.00'),
                    description=f"Purchase from {transaction_obj.customer.name}"
                )
                
                # Credit: Main Accounts Payable
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=main_ap_account,
                    debit=Decimal('0.00'),
                    credit=transaction_obj.total_amount,
                    description=f"Purchase from {transaction_obj.customer.name}"
                )
                
                return journal_entry
                
    except Exception as e:
        raise ValueError(f"Error creating transaction journal entry: {str(e)}")
    
@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT])
def record_vendor_payment(request, pk):
    """Record payment for vendor transaction (purchase/bill)"""
    customer = get_object_or_404(Customer, pk=pk, company=request.user.company)
    
    if request.method == 'POST':
        transaction_id = request.POST.get('transaction_id')
        amount = Decimal(request.POST.get('amount', '0'))
        payment_date = request.POST.get('payment_date')
        payment_notes = request.POST.get('notes', '')
        
        transaction_obj = get_object_or_404(
            Transaction, 
            id=transaction_id, 
            customer=customer,
            company=request.user.company
        )
        
        if amount <= 0:
            messages.error(request, "Payment amount must be greater than zero")
        elif amount > transaction_obj.balance_due:
            currency_symbol = get_currency_symbol(request.user.company.currency)
            messages.error(request, f"Payment amount cannot exceed balance due of {currency_symbol}{transaction_obj.balance_due}")
        else:
            try:
                with db_transaction.atomic():
                    # Record payment on original transaction
                    transaction_obj.amount_paid += amount
                    transaction_obj.save()
                    
                    # Create payment transaction for history
                    payment_transaction = Transaction.objects.create(
                        company=request.user.company,
                        customer=customer,
                        transaction_type=TransactionType.PAYMENT,
                        date=payment_date or timezone.now().date(),
                        description=f"Payment made for Transaction #{transaction_obj.id}",
                        reference_number=f"PMT-{transaction_obj.id}-{timezone.now().strftime('%Y%m%d')}",
                        total_amount=amount,
                        amount_paid=amount,
                        created_by=request.user
                    )
                    
                    # Update customer balances
                    customer.update_balances()
                    
                    # Create journal entry for VENDOR payment
                    journal_entry = create_vendor_payment_journal_entry(transaction_obj, amount)
                    journal_entry.created_by = request.user
                    journal_entry.save()

                    currency_symbol = get_currency_symbol(request.user.company.currency)
                    messages.success(
                        request, 
                        f"Payment of {currency_symbol}{amount} recorded successfully for Transaction #{transaction_obj.id}"
                    )
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"An error occurred while recording payment: {str(e)}")
    
    return redirect('customers:customer-detail', pk=pk)


@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT])
def customer_delete(request, pk):
    company = get_current_company(request)
    if not company: return redirect('customers:customer-list')
    customer = get_object_or_404(Customer, pk=pk, company=company)

    if customer.receivable_balance != Decimal('0.00') or customer.payable_balance != Decimal('0.00'):
        messages.error(request, f"Cannot delete {customer.name}. They have an outstanding balance. Please clear all invoices and bills first.")
        return redirect('customers:customer-detail', pk=customer.pk)

    if request.method == 'POST':
        customer_name = customer.name
        if customer.receivable_account: customer.receivable_account.delete()
        if customer.payable_account: customer.payable_account.delete()
        
        customer.delete()
        messages.success(request, f"Successfully deleted {customer_name}.")
        return redirect('customers:customer-list')

    return render(request, 'customers/customer_confirm_delete.html', {'customer': customer})

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT])
def send_reminder_email(request, pk):
    """
    Sends a payment reminder email to a customer for OVERDUE invoices,
    while also showing their total outstanding balance.
    """
    company = get_current_company(request)
    if not company: return redirect('customers:customer-list')
    
    customer = get_object_or_404(Customer, pk=pk, company=company)

    if not customer.email:
        messages.error(request, f"{customer.name} does not have an email address on file. Cannot send reminder.")
        return redirect('customers:customer-detail', pk=customer.pk)

    today = timezone.now().date()
    
    # 🎯 FIX: Use the correct transaction type constant
    overdue_transactions = Transaction.objects.filter(
        company=company,
        customer=customer,
        transaction_type=TransactionType.SALE,  # ✅ USE CONSTANT FROM IMPORTED CLASS
        due_date__lt=today
    ).exclude(
        amount_paid__gte=F('total_amount')
    )

    if not overdue_transactions.exists():
        messages.info(request, f"{customer.name} has no overdue invoices. No reminder sent.")
        return redirect('customers:customer-detail', pk=customer.pk)

    # Calculate the total amount that is specifically overdue
    total_overdue_balance = sum(t.balance_due for t in overdue_transactions)

    # --- THIS IS THE KEY ADDITION ---
    # Get the customer's total balance for context in the email.
    total_receivable_balance = customer.receivable_balance
    # --- END ADDITION ---

    # Send the email with the new, more detailed context
    success = send_email(
        subject=f"Payment Reminder from {company.name}",
        template_name='emails/debtor_reminder.html',
        context={
            'company_name': company.name,
            'company_email': company.email,
            'company_phone': company.phone,
            'customer_name': customer.name,
            'total_balance': total_receivable_balance, # Pass the total balance
            'total_overdue_balance': total_overdue_balance, # Pass the overdue portion
            'overdue_transactions': overdue_transactions, # Pass the list of overdue items
            'currency_symbol': request.user.company.currency,
        },
        to_emails=[customer.email]
    )

    if success:
        messages.success(request, f"A payment reminder for {overdue_transactions.count()} overdue invoice(s) has been sent to {customer.name}.")
    else:
        messages.error(request, "There was an error sending the reminder email. Please try again later.")
        
    return redirect('customers:customer-detail', pk=customer.pk)

def export_customers(request):
    """Export customers in requested format - FIXED VERSION"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    customers = Customer.objects.filter(company=company).order_by('name')
    
    headers = ['Name', 'Type', 'Email', 'Phone', 'Address', 'Receivable Balance', 'Payable Balance', 'Credit Limit']
    data = []
    
    for customer in customers:
        try:
            data.append([
                customer.name,
                customer.get_entity_type_display(),
                customer.email or '',
                customer.phone or '',
                customer.address or '',
                float(customer.receivable_balance),  # ✅ Using database field
                float(customer.payable_balance),    # ✅ Using database field
                float(customer.credit_limit)
            ])
        except Exception as e:
            print(f"Error processing customer {customer.name}: {e}")
            continue
    
    filename = f"customers_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Customer List"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Customers", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)

def export_customer_statement(request, pk):
    """Export individual customer statement"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    customer = get_object_or_404(Customer, pk=pk, company=company)
    
    transactions = Transaction.objects.filter(customer=customer).order_by('-date')
    
    headers = ['Date', 'Type', 'Reference', 'Description', 'Amount', 'Paid', 'Balance Due']
    data = []
    
    # Add customer header info
    data.append(['Customer Statement for:', customer.name, '', '', '', '', ''])
    data.append(['Email:', customer.email or 'N/A', '', '', '', '', ''])
    data.append(['Phone:', customer.phone or 'N/A', '', '', '', '', ''])
    data.append(['', '', '', '', '', '', ''])
    
    for transaction in transactions:
        data.append([
            transaction.date,
            transaction.get_transaction_type_display(),
            transaction.reference_number or '',
            transaction.description or '',
            transaction.total_amount,
            transaction.amount_paid,
            transaction.balance_due
        ])
    
    # Add summary
    data.append(['', '', '', '', '', '', ''])
    data.append(['Total Outstanding:', '', '', '', '', '', customer.receivable_balance])
    
    filename = f"customer_statement_{customer.name.lower().replace(' ', '_')}_{date.today()}"
    title = f"Customer Statement - {customer.name}"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Customer Statement", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)
