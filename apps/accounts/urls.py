# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\accounts\urls.py

from django.urls import path
from .views import (
    chart_of_accounts_list,
    AccountCreateView,
    AccountUpdateView,
    AccountDeleteView,
)
from . import views

app_name = 'accounts'

urlpatterns = [
    # The main list view
    path('', chart_of_accounts_list, name='chart-of-accounts'),
    path('create/', AccountCreateView.as_view(), name='account-create'),
    path('<int:pk>/update/', AccountUpdateView.as_view(), name='account-update'),
    path('<int:pk>/delete/', AccountDeleteView.as_view(), name='account-delete'),

    path('<int:pk>/debug/', views.debug_account_balance, name='debug-balance'),

    path('export/', views.export_chart_of_accounts, name='export'),
    path('<int:pk>/export-transactions/', views.export_account_transactions, name='export-transactions'),
]
