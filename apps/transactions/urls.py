# In C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\transactions\urls.py

from django.urls import path
from .views import (TransactionListView, TransactionDetailView, TransactionCreateView, TransactionUpdateView, TransactionDeleteView,
    TransactionCategoryListView, TransactionCategoryCreateView, TransactionCategoryUpdateView, TransactionCategoryDetailView, RecordPaymentView)
from . import views, api_views

app_name = 'transactions'

urlpatterns = [
    path('', TransactionListView.as_view(), name='transaction_list'),
    path('create/', TransactionCreateView.as_view(), name='transaction_create'),
    path('<int:pk>/', TransactionDetailView.as_view(), name='transaction_detail'),
    # --- CRITICAL FIX: Point this URL to the correct view ---
    path('<int:pk>/update/', TransactionUpdateView.as_view(), name='transaction_update'), # Changed from TransactionDeleteView
    # --- END FIX ---
    path('<int:pk>/record-payment/', RecordPaymentView.as_view(), name='record_payment'),
    path('<int:pk>/delete/', TransactionDeleteView.as_view(), name='transaction_delete'),
    path('<int:pk>/invoice/', views.TransactionInvoiceView.as_view(), name='transaction_invoice'),

    path('export/', views.export_transactions, name='export'),
    path('<int:pk>/export-detail/', views.export_transaction_detail, name='export-detail'),
    path('api/accounts-by-type/<int:account_type_id>/', views.accounts_by_type_api, name='accounts_by_type_api'),

    path('categories/', TransactionCategoryListView.as_view(), name='category_list'),
    path('categories/create/', TransactionCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/', TransactionCategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:pk>/edit/', TransactionCategoryUpdateView.as_view(), name='category_update'),

    path('api/search/', api_views.transaction_search_api, name='api_search'),
]
