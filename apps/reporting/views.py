# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\reporting\views.py
from django.shortcuts import render
from django.db.models import Sum, Q
from apps.accounts.models import Account, AccountType
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from apps.authentication.decorators import user_type_required
from apps.authentication.models import User
from .export_utils import export_to_csv, export_to_excel, export_to_pdf, export_hierarchical_to_excel
from datetime import date
from apps.journal.models import JournalEntryLine
from apps.core.models import Company

import logging
logger = logging.getLogger(__name__)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def trial_balance_view(request):
    """
    This view prepares the data for the Trial Balance report.
    """
    try:
        logger.info(f"Trial balance view accessed by user: {request.user}")
        
        company = request.user.company
        logger.info(f"User company: {company}")
        
        # Import currency utilities
        from apps.core.utils import safe_decimal
        
        # Initialize default values
        total_debits = safe_decimal(0)
        total_credits = safe_decimal(0)
        
        context = {
            'company_name': "No Company Found",
            'report_lines': [],
            'total_debits': total_debits,
            'total_credits': total_credits,
            'difference': abs(total_debits - total_credits),
        }

        if company:
            logger.info(f"Processing accounts for company: {company.name}")
            accounts = Account.objects.filter(company=company).order_by('account_number')
            logger.info(f"Found {accounts.count()} accounts")
            
            report_lines = []
            total_debits = safe_decimal(0)
            total_credits = safe_decimal(0)
            
            for account in accounts:
                try:
                    balance = safe_decimal(account.get_balance())
                    logger.debug(f"Account {account.name}: balance = {balance}")
                    
                    if balance == 0:
                        continue

                    # ONLY include accounts that have direct journal entries (leaf accounts)
                    has_transactions = account.journal_lines.exists()
                    if not has_transactions:
                        continue
                        
                    debit_balance = safe_decimal(0)
                    credit_balance = safe_decimal(0)
                    
                    # For trial balance, show the natural balance side
                    if account.account_type.category in [AccountType.Category.ASSET, AccountType.Category.EXPENSE]:
                        if balance >= 0:
                            debit_balance = balance
                            total_debits += balance
                        else:
                            # Negative asset/expense balance goes on credit side
                            credit_balance = abs(balance)
                            total_credits += abs(balance)
                    else:
                        if balance >= 0:
                            credit_balance = balance
                            total_credits += balance
                        else:
                            # Negative liability/equity/revenue balance goes on debit side
                            debit_balance = abs(balance)
                            total_debits += abs(balance)
                        
                    report_lines.append({
                        'code': account.account_number,
                        'name': account.name,
                        'debit': debit_balance,
                        'credit': credit_balance,
                    })
                except Exception as e:
                    logger.error(f"Error processing account {account.name}: {str(e)}")
                    continue
                
            # Calculate the difference
            difference = abs(total_debits - total_credits)
                
            context.update({
                'company_name': company.name,
                'report_lines': report_lines,
                'total_debits': total_debits,
                'total_credits': total_credits,
                'difference': difference,
            })
            
            logger.info(f"Trial balance completed. Total lines: {len(report_lines)}")
            logger.info(f"Total debits: {total_debits}, Total credits: {total_credits}, Difference: {difference}")
        
        return render(request, 'reporting/trial_balance.html', context)
        
    except Exception as e:
        logger.error(f"Critical error in trial_balance_view: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def general_ledger(request):
    """
    This view prepares the data for the General Ledger report.
    """
    company = request.user.company
    
    # Import currency utilities
    from apps.core.utils import safe_decimal
    
    context = {
        'company_name': "No Company Found",
        'report_lines': [],
        'total_transactions': 0,
        'today': date.today(),
    }

    if company:
        accounts_with_transactions = Account.objects.filter(
            company=company,
            journal_lines__isnull=False
        ).distinct().order_by('account_number')

        report_lines = []
        total_transactions = 0  # Initialize counter
        
        for account in accounts_with_transactions:
            lines = JournalEntryLine.objects.filter(account=account).order_by('journal_entry__date', 'id')
            
            running_balance = safe_decimal(0)
            transaction_lines = []
            total_debits = safe_decimal(0)
            total_credits = safe_decimal(0)

            # Determine if this is a credit balance account
            is_credit_balance_account = account.account_type.category in [
                AccountType.Category.LIABILITY, 
                AccountType.Category.EQUITY, 
                AccountType.Category.REVENUE
            ]

            for line in lines:
                # Calculate running balance
                if is_credit_balance_account:
                    running_balance += (safe_decimal(line.credit) - safe_decimal(line.debit))
                else:
                    running_balance += (safe_decimal(line.debit) - safe_decimal(line.credit))

                # Sum totals for summary
                total_debits += safe_decimal(line.debit)
                total_credits += safe_decimal(line.credit)

                transaction_lines.append({
                    'date': line.journal_entry.date,
                    'description': line.journal_entry.description,
                    'reference': getattr(line.journal_entry, 'reference', ''),  # Add reference if available
                    'debit': safe_decimal(line.debit),
                    'credit': safe_decimal(line.credit),
                    'balance': running_balance,
                })
            
            # Count total transactions
            total_transactions += len(transaction_lines)
            
            report_lines.append({
                'account_code': account.account_number,
                'account_name': account.name,
                'transactions': transaction_lines,
                'final_balance': running_balance,
                'total_debits': total_debits,  # Add this for summary
                'total_credits': total_credits,  # Add this for summary
                'is_credit_account': is_credit_balance_account,
            })

        context.update({
            'company_name': company.name,
            'report_lines': report_lines,
            'total_transactions': total_transactions,  # Pass the total count
        })

    return render(request, 'reporting/general_ledger.html', context)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def income_statement(request):
    """
    This view prepares the data for the Income Statement report.
    """
    company = request.user.company
    
    # Import currency utilities
    from apps.core.utils import safe_decimal

    context = {
        'company_name': "No Company Found",
        'revenue_lines': [],
        'total_revenue': safe_decimal(0),
        'expense_lines': [],
        'total_expenses': safe_decimal(0),
        'net_income': safe_decimal(0),
        'is_profit': False,
    }

    if company:
        accounts = Account.objects.filter(company=company)
        report_accounts = accounts.filter(
            account_type__category__in=[AccountType.Category.REVENUE, AccountType.Category.EXPENSE]
        )
        
        account_balances = report_accounts.annotate(
            calculated_balance=Sum('journal_lines__credit', default=0) - Sum('journal_lines__debit', default=0)
        ).exclude(calculated_balance=0)

        revenue_lines = []
        total_revenue = safe_decimal(0)
        expense_lines = []
        total_expenses = safe_decimal(0)

        for account in account_balances:
            if account.account_type.category == AccountType.Category.REVENUE:
                # Revenue: Credit balance is positive
                balance = safe_decimal(account.calculated_balance)
                total_revenue += balance
                revenue_lines.append({
                    'code': account.account_number,
                    'name': account.name,
                    'balance': balance,
                })
            elif account.account_type.category == AccountType.Category.EXPENSE:
                # Expense: Debit balance is positive, so flip the sign
                balance = safe_decimal(account.calculated_balance) * -1
                total_expenses += balance
                expense_lines.append({
                    'code': account.account_number,
                    'name': account.name,
                    'balance': balance,
                })

        net_income = total_revenue - total_expenses
        
        context.update({
            'company_name': company.name, 
            'revenue_lines': revenue_lines,
            'total_revenue': total_revenue,
            'expense_lines': expense_lines,
            'total_expenses': total_expenses,
            'net_income': net_income,
            'is_profit': net_income >= 0,
        })
    
    return render(request, 'reporting/income_statement.html', context)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def balance_sheet(request):
    """
    This view prepares the data for the Balance Sheet report.
    FIXED: Only includes leaf accounts to prevent double-counting in hierarchical structures
    """
    company = request.user.company
    
    # Import currency utilities
    from apps.core.utils import safe_decimal
    
    context = {
        'company_name': "No Company Found",
        'today': date.today(),
        'currency_symbol': '₦',  # Add default currency symbol
    }

    if company:
        # 🎯 CRITICAL FIX: Only get accounts that have actual journal entries (leaf accounts)
        # This prevents double-counting parent/child account relationships
        accounts_with_transactions = Account.objects.filter(
            company=company,
            journal_lines__isnull=False  # Only accounts with actual transactions
        ).exclude(
            account_type__category__in=[AccountType.Category.REVENUE, AccountType.Category.EXPENSE]
        ).distinct().order_by('account_number')

        # Calculate Retained Earnings (Net Income) from Revenue and Expense accounts
        revenue_accounts = Account.objects.filter(
            company=company, 
            account_type__category=AccountType.Category.REVENUE,
            journal_lines__isnull=False  # Only accounts with transactions
        ).distinct()
        
        expense_accounts = Account.objects.filter(
            company=company, 
            account_type__category=AccountType.Category.EXPENSE,
            journal_lines__isnull=False  # Only accounts with transactions
        ).distinct()
        
        total_revenue = sum(safe_decimal(account.get_balance()) for account in revenue_accounts)
        total_expenses = sum(safe_decimal(account.get_balance()) for account in expense_accounts)
        retained_earnings = total_revenue - total_expenses

        # Categorize accounts and calculate totals
        asset_lines = []
        liability_lines = []
        equity_lines = []
        total_assets = safe_decimal(0)
        total_liabilities = safe_decimal(0)
        base_equity = safe_decimal(0)

        for account in accounts_with_transactions:
            balance = safe_decimal(account.get_balance())
            if balance == 0:
                continue

            line_item = {
                'code': account.account_number,
                'name': account.name, 
                'balance': abs(balance)
            }

            if account.account_type.category == AccountType.Category.ASSET:
                asset_lines.append(line_item)
                total_assets += abs(balance)
            
            elif account.account_type.category == AccountType.Category.LIABILITY:
                liability_lines.append(line_item)
                total_liabilities += abs(balance)

            elif account.account_type.category == AccountType.Category.EQUITY:
                equity_lines.append(line_item)
                base_equity += abs(balance)

        # Calculate final equity
        total_equity = base_equity + retained_earnings
        total_liabilities_and_equity = total_liabilities + total_equity

        # Add currency symbol from company
        currency_symbol = '₦'  # Default
        if hasattr(company, 'currency'):
            currency_symbols = {
                'NGN': '₦',
                'USD': '$',
                'GBP': '£',
                'EUR': '€',
            }
            currency_symbol = currency_symbols.get(company.currency, company.currency)

        context.update({
            'company_name': company.name,
            'asset_lines': asset_lines,
            'liability_lines': liability_lines,
            'equity_lines': equity_lines,
            'retained_earnings': retained_earnings,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'total_liabilities_and_equity': total_liabilities_and_equity,
            'currency_symbol': currency_symbol,
        })

    return render(request, 'reporting/balance_sheet.html', context)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def export_trial_balance(request):
    """Export trial balance in requested format"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    # --- FIX: Only include accounts that have journal entries (leaf accounts) ---
    # This prevents double-counting parent accounts and aligns with the on-screen view.
    accounts = Account.objects.filter(
        company=company,
        journal_lines__isnull=False  # This is the critical filter
    ).distinct().order_by('account_number')
    
    headers = ['Account Code', 'Account Name', 'Debit', 'Credit']
    data = []
    total_debits = 0
    total_credits = 0
    
    for account in accounts:
        # The get_balance() method is now safe to use because we are only iterating over leaf accounts.
        balance = account.get_balance()
        
        # We can skip the 'if balance == 0' check because the journal_lines__isnull=False
        # filter already implies the account has activity.
            
        debit_balance = 0
        credit_balance = 0
        
        if account.account_type.category in [AccountType.Category.ASSET, AccountType.Category.EXPENSE]:
            if balance >= 0:
                debit_balance = balance
                total_debits += balance
            else:
                credit_balance = abs(balance)
                total_credits += abs(balance)
        else:
            if balance >= 0:
                credit_balance = balance
                total_credits += balance
            else:
                debit_balance = abs(balance)
                total_debits += abs(balance)
        
        data.append([
            account.account_number,
            account.name,
            debit_balance if debit_balance > 0 else '',
            credit_balance if credit_balance > 0 else ''
        ])
    
    # Add totals row
    data.append(['', 'TOTALS', total_debits, total_credits])
    
    filename = f"trial_balance_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Trial Balance"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Trial Balance", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def export_income_statement(request):
    """Export income statement in requested format"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company  # 🎯 FIX: Remove duplicate assignment
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    headers = ['Account Code', 'Account Name', 'Amount']
    data = []
    
    # Revenue section
    data.append(['', '=== REVENUE ===', ''])
    revenue_accounts = Account.objects.filter(
        company=company,  # 🎯 FIX: Use company object directly
        account_type__category=AccountType.Category.REVENUE
    ).annotate(
        calculated_balance=Sum('journal_lines__credit', default=0) - Sum('journal_lines__debit', default=0)
    ).exclude(calculated_balance=0)
    
    total_revenue = 0
    for account in revenue_accounts:
        balance = account.calculated_balance
        total_revenue += balance
        data.append([account.account_number, account.name, balance])
    
    data.append(['', 'Total Revenue', total_revenue])
    data.append(['', '', ''])
    
    # Expense section
    data.append(['', '=== EXPENSES ===', ''])
    expense_accounts = Account.objects.filter(
        company=company,  # 🎯 FIX: Use company object directly
        account_type__category=AccountType.Category.EXPENSE
    ).annotate(
        calculated_balance=Sum('journal_lines__credit', default=0) - Sum('journal_lines__debit', default=0)
    ).exclude(calculated_balance=0)
    
    total_expenses = 0
    for account in expense_accounts:
        balance = account.calculated_balance * -1
        total_expenses += balance
        data.append([account.account_number, account.name, balance])
    
    data.append(['', 'Total Expenses', total_expenses])
    data.append(['', '', ''])
    
    net_income = total_revenue - total_expenses
    data.append(['', '=== NET INCOME ===', net_income])
    
    filename = f"income_statement_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Income Statement"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Income Statement", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def export_general_ledger(request):
    """Export general ledger in requested format"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company  # 🎯 FIX: Remove duplicate assignment
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)
    
    accounts_with_transactions = Account.objects.filter(
        company=company,  # 🎯 FIX: Use company object directly
        journal_lines__isnull=False
    ).distinct().order_by('account_number')

    filename = f"general_ledger_{company.name.lower().replace(' ', '_')}_{date.today()}"
    
    if format_type == 'excel':
        # Use hierarchical export for Excel
        report_lines = []
        for account in accounts_with_transactions:
            lines = JournalEntryLine.objects.filter(account=account).order_by('journal_entry__date', 'id')
            
            running_balance = 0
            transaction_lines = []

            is_credit_balance_account = account.account_type.category in [
                AccountType.Category.LIABILITY, 
                AccountType.Category.EQUITY, 
                AccountType.Category.REVENUE
            ]

            for line in lines:
                if is_credit_balance_account:
                    running_balance += (line.credit - line.debit)
                else:
                    running_balance += (line.debit - line.credit)

                transaction_lines.append({
                    'date': line.journal_entry.date,
                    'description': line.journal_entry.description,
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': running_balance,
                })
            
            report_lines.append({
                'account_code': account.account_number,
                'account_name': account.name,
                'transactions': transaction_lines,
                'final_balance': running_balance,
            })
        
        return export_hierarchical_to_excel(report_lines, filename, "General Ledger", company.name)
    
    else:
        # For CSV and PDF, flatten the data
        headers = ['Account Code', 'Account Name', 'Date', 'Description', 'Debit', 'Credit', 'Balance']
        data = []
        
        for account in accounts_with_transactions:
            lines = JournalEntryLine.objects.filter(account=account).order_by('journal_entry__date', 'id')
            
            running_balance = 0
            is_credit_balance_account = account.account_type.category in [
                AccountType.Category.LIABILITY, 
                AccountType.Category.EQUITY, 
                AccountType.Category.REVENUE
            ]
            
            # Add account header
            data.append([f"{account.account_number} - {account.name}", '', '', '', '', '', ''])
            
            for line in lines:
                if is_credit_balance_account:
                    running_balance += (line.credit - line.debit)
                else:
                    running_balance += (line.debit - line.credit)

                data.append([
                    '',
                    '',
                    line.journal_entry.date,
                    line.journal_entry.description,
                    line.debit if line.debit > 0 else '',
                    line.credit if line.credit > 0 else '',
                    running_balance
                ])
            
            # Add final balance
            data.append(['', '', '', 'Final Balance:', '', '', running_balance])
            data.append(['', '', '', '', '', '', ''])  # Spacer
        
        title = "General Ledger"
        
        if format_type == 'csv':
            return export_to_csv(data, filename, headers)
        elif format_type == 'pdf':
            return export_to_pdf(data, filename, headers, title, company.name)
        else:
            return JsonResponse({'error': 'Invalid format'}, status=400)

@login_required
@user_type_required(allowed_roles=[User.UserType.ADMIN, User.UserType.ACCOUNTANT, User.UserType.MANAGER, User.UserType.VIEWER])
def export_balance_sheet(request):
    """Export balance sheet in requested format"""
    format_type = request.GET.get('format', 'csv')
    company = request.user.company
    
    if not company:
        return JsonResponse({'error': 'No company found'}, status=400)

    # --- FIX: Use the same correct logic as the on-screen view ---
    # 1. Only get accounts that have actual journal entries (leaf accounts).
    # This is the critical fix to prevent double-counting parent accounts.
    accounts_with_transactions = Account.objects.filter(
        company=company,
        journal_lines__isnull=False
    ).exclude(
        account_type__category__in=[AccountType.Category.REVENUE, AccountType.Category.EXPENSE]
    ).distinct().order_by('account_number')

    # 2. Calculate Retained Earnings using the same robust method as the view.
    revenue_accounts = Account.objects.filter(
        company=company, 
        account_type__category=AccountType.Category.REVENUE,
        journal_lines__isnull=False
    ).distinct()
    
    expense_accounts = Account.objects.filter(
        company=company, 
        account_type__category=AccountType.Category.EXPENSE,
        journal_lines__isnull=False
    ).distinct()
    
    total_revenue = sum(account.get_balance() for account in revenue_accounts)
    total_expenses = sum(account.get_balance() for account in expense_accounts)
    retained_earnings = total_revenue - total_expenses

    headers = ['Account Code', 'Account Name', 'Amount']
    data = []
    
    # --- ASSETS ---
    data.append(['', '=== ASSETS ===', ''])
    total_assets = 0
    for account in accounts_with_transactions:
        if account.account_type.category == AccountType.Category.ASSET:
            balance = account.get_balance()
            if balance != 0:
                data.append([account.account_number, account.name, abs(balance)])
                total_assets += abs(balance)
    data.append(['', 'Total Assets', total_assets])
    data.append(['', '', ''])
    
    # --- LIABILITIES ---
    data.append(['', '=== LIABILITIES ===', ''])
    total_liabilities = 0
    for account in accounts_with_transactions:
        if account.account_type.category == AccountType.Category.LIABILITY:
            balance = account.get_balance()
            if balance != 0:
                data.append([account.account_number, account.name, abs(balance)])
                total_liabilities += abs(balance)
    data.append(['', 'Total Liabilities', total_liabilities])
    data.append(['', '', ''])
    
    # --- EQUITY ---
    data.append(['', '=== EQUITY ===', ''])
    base_equity = 0
    for account in accounts_with_transactions:
        if account.account_type.category == AccountType.Category.EQUITY:
            balance = account.get_balance()
            if balance != 0:
                data.append([account.account_number, account.name, abs(balance)])
                base_equity += abs(balance)
    
    data.append(['', 'Retained Earnings', retained_earnings])
    total_equity = base_equity + retained_earnings
    data.append(['', 'Total Equity', total_equity])
    data.append(['', '', ''])
    data.append(['', 'Total Liabilities & Equity', total_liabilities + total_equity])
    
    filename = f"balance_sheet_{company.name.lower().replace(' ', '_')}_{date.today()}"
    title = "Balance Sheet"
    
    if format_type == 'csv':
        return export_to_csv(data, filename, headers)
    elif format_type == 'excel':
        return export_to_excel(data, filename, headers, "Balance Sheet", company.name)
    elif format_type == 'pdf':
        return export_to_pdf(data, filename, headers, title, company.name)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)