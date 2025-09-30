# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\reporting\urls.py
from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # Report views
    path('trial-balance/', views.trial_balance_view, name='trial-balance'),
    path('income-statement/', views.income_statement, name='income-statement'),
    path('general-ledger/', views.general_ledger, name='general-ledger'),
    path('balance-sheet/', views.balance_sheet, name='balance-sheet'),
    
    # Export URLs
    path('export/trial-balance/', views.export_trial_balance, name='export-trial-balance'),
    path('export/income-statement/', views.export_income_statement, name='export-income-statement'),
    path('export/general-ledger/', views.export_general_ledger, name='export-general-ledger'),
    path('export/balance-sheet/', views.export_balance_sheet, name='export-balance-sheet'),
]