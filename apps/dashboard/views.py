# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\dashboard\views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import json
from calendar import month_name

# Import models from other apps to gather data
from apps.accounts.models import Account, AccountType
from apps.customers.models import Customer
from apps.inventory.models import InventoryItem
from apps.transactions.models import Transaction
from apps.subscriptions.utils import has_production_access

try:
    from apps.production.models import ProductionFormula, ProductionOrder
except ImportError:
    ProductionFormula = None
    ProductionOrder = None

@login_required
def dashboard_home(request):
    """
    Enhanced dashboard with charts and comprehensive metrics
    Uses centralized currency system from context processor
    """
    company = request.user.company
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    if not company:
        # Fallback for users without company
        context = {
            'page_title': 'Dashboard',
            'error_message': 'No company associated with your account.',
            'cash_at_bank': Decimal('0.00'),
            'accounts_receivable': Decimal('0.00'),
            'accounts_payable': Decimal('0.00'),
            'active_customers': 0,
            'inventory_items': 0,
            'overdue_bills_count': 0,
        }
        return render(request, 'dashboard/home.html', context)
    
    # --- Enhanced Balance Calculations ---
    # Use system accounts for more reliable lookups
    try:
        cash_account = Account.objects.get(company=company, system_account=Account.SystemAccount.DEFAULT_CASH)
        cash_balance = cash_account.get_balance()
    except Account.DoesNotExist:
        # Fallback to account type lookup
        cash_accounts = Account.objects.filter(company=company, account_type__name__icontains='Bank')
        cash_balance = sum(acc.get_balance() for acc in cash_accounts)
    
    try:
        ar_account = Account.objects.get(company=company, system_account=Account.SystemAccount.ACCOUNTS_RECEIVABLE)
        ar_balance = ar_account.get_balance()
    except Account.DoesNotExist:
        ar_accounts = Account.objects.filter(company=company, account_type__name__icontains='Receivable')
        ar_balance = sum(acc.get_balance() for acc in ar_accounts)
    
    try:
        ap_account = Account.objects.get(company=company, system_account=Account.SystemAccount.ACCOUNTS_PAYABLE)
        ap_balance = ap_account.get_balance()
    except Account.DoesNotExist:
        ap_accounts = Account.objects.filter(company=company, account_type__name__icontains='Payable')
        ap_balance = sum(acc.get_balance() for acc in ap_accounts)
    
    # --- Customer and Inventory Counts ---
    total_customers = Customer.objects.filter(company=company).count()
    total_inventory_items = InventoryItem.objects.filter(company=company).count()
    
    # --- Time-based analysis for charts ---
    monthly_income_data = get_monthly_income_data(company)
    monthly_expense_data = get_monthly_expense_data(company)
    cash_flow_data = get_cash_flow_trend(company)
    
    # --- Alert metrics ---
    overdue_invoices_count = Transaction.objects.filter(
        company=company,
        transaction_type='SALE',
        due_date__lt=today,
        amount_paid__lt=F('total_amount')
    ).count()
    
    # 🆕 ADD THIS - OVERDUE BILLS COUNT
    overdue_bills_count = Transaction.objects.filter(
        company=company,
        transaction_type='PURCHASE',
        due_date__lt=today,
        amount_paid__lt=F('total_amount')
    ).count()
    
    low_stock_items_count = InventoryItem.objects.filter(
        company=company,
        quantity_on_hand__lte=F('reorder_level'),
        item_type=InventoryItem.is_product
    ).count()
    
    # --- Recent activity ---
    recent_transactions = Transaction.objects.filter(
        company=company
    ).select_related('customer', 'category').order_by('-created_at')[:5]
    
    # --- This month vs last month comparison ---
    current_month_start = today.replace(day=1)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    
    current_month_income = get_period_income(company, current_month_start, today)
    last_month_income = get_period_income(company, last_month_start, current_month_start - timedelta(days=1))
    
    current_month_expenses = get_period_expenses(company, current_month_start, today)
    last_month_expenses = get_period_expenses(company, last_month_start, current_month_start - timedelta(days=1))

    production_stats = None
    if has_production_access(request.user) and ProductionFormula is not None:
        production_stats = {
            'formulas_count': ProductionFormula.objects.filter(company=company).count(),
            'planned_orders': ProductionOrder.objects.filter(
                company=company, 
                status=ProductionOrder.Status.PLANNED
            ).count(),
            'completed_orders': ProductionOrder.objects.filter(
                company=company,
                status=ProductionOrder.Status.COMPLETED,
                completion_date__gte=thirty_days_ago
            ).count(),
            'recent_productions': ProductionOrder.objects.filter(
                company=company,
                status=ProductionOrder.Status.COMPLETED
            ).order_by('-completion_date')[:5]
        }
    
    # --- 🎯 CLEAN CONTEXT - No duplicate currency logic ---
    context = {
        'page_title': 'Dashboard',
        
        # --- Core Financial Metrics ---
        'cash_at_bank': cash_balance,
        'accounts_receivable': ar_balance,
        'accounts_payable': ap_balance,
        'active_customers': total_customers,
        'inventory_items': total_inventory_items,
        
        # --- Chart Data (JSON serialized for JavaScript) ---
        'monthly_labels': json.dumps(monthly_income_data['labels']),
        'monthly_income': json.dumps(monthly_income_data['data']),
        'monthly_expenses': json.dumps(monthly_expense_data['data']),
        'cash_flow_labels': json.dumps(cash_flow_data['labels']),
        'cash_flow_data': json.dumps(cash_flow_data['data']),
        
        # --- Alert Metrics ---
        'overdue_invoices_count': overdue_invoices_count,
        'overdue_bills_count': overdue_bills_count,
        'low_stock_items_count': low_stock_items_count,
        
        # --- Recent Activity ---
        'recent_transactions': recent_transactions,
        
        # --- Period Comparisons ---
        'current_month_income': current_month_income,
        'last_month_income': last_month_income,
        'current_month_expenses': current_month_expenses,
        'last_month_expenses': last_month_expenses,
        'income_trend': 'up' if current_month_income > last_month_income else 'down',
        'expense_trend': 'up' if current_month_expenses > last_month_expenses else 'down',
        
        # --- Quick Stats ---
        'net_income_this_month': current_month_income - current_month_expenses,
        'total_transactions_count': Transaction.objects.filter(company=company).count(),
        
        # --- Production Stats ---
        'production_stats': production_stats,
    }
    
    return render(request, 'dashboard/home.html', context)


def get_monthly_income_data(company):
    """Get last 12 months income data for charts"""
    today = timezone.now().date()
    months_data = []
    labels = []
    
    for i in range(11, -1, -1):  # Last 12 months
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        
        # Get next month start for range
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
        
        # Calculate income for this month
        income = Transaction.objects.filter(
            company=company,
            transaction_type='SALE',
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        months_data.append(float(income))
        labels.append(month_name[month_date.month][:3])  # Short month name
    
    return {'data': months_data, 'labels': labels}

def get_monthly_expense_data(company):
    """Get last 12 months expense data for charts"""
    today = timezone.now().date()
    months_data = []
    
    for i in range(11, -1, -1):  # Last 12 months
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        
        # Get next month start for range
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
        
        # Calculate expenses for this month
        expenses = Transaction.objects.filter(
            company=company,
            transaction_type__in=['PURCHASE', 'EXPENSE'],
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        months_data.append(float(expenses))
    
    return {'data': months_data}

def get_cash_flow_trend(company):
    """Get cash flow trend for last 12 months"""
    today = timezone.now().date()
    cash_flow_data = []
    labels = []
    
    for i in range(11, -1, -1):  # Last 12 months
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
        
        # Income
        income = Transaction.objects.filter(
            company=company,
            transaction_type='SALE',
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Expenses
        expenses = Transaction.objects.filter(
            company=company,
            transaction_type__in=['PURCHASE', 'EXPENSE'],
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        net_cash_flow = float(income - expenses)
        cash_flow_data.append(net_cash_flow)
        labels.append(month_name[month_date.month][:3])
    
    return {'data': cash_flow_data, 'labels': labels}

def get_period_income(company, start_date, end_date):
    """Get total income for a specific period"""
    income = Transaction.objects.filter(
        company=company,
        transaction_type='SALE',
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    return income

def get_period_expenses(company, start_date, end_date):
    """Get total expenses for a specific period"""
    expenses = Transaction.objects.filter(
        company=company,
        transaction_type__in=['PURCHASE', 'EXPENSE'],
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    return expenses
