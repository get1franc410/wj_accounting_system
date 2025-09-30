# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\customers\urls.py

from django.urls import path
from . import views, api_views

app_name = 'customers'

urlpatterns = [
    path('', views.customer_list, name='customer-list'),
    path('create/', views.customer_create, name='customer-create'),
    path('<int:pk>/', views.customer_detail, name='customer-detail'),
    path('<int:pk>/edit/', views.customer_update, name='customer-update'),
    path('<int:pk>/delete/', views.customer_delete, name='customer-delete'),
    path('<int:pk>/send-reminder/', views.send_reminder_email, name='send-reminder-email'),

    path('export/', views.export_customers, name='export'),
    path('<int:pk>/export-statement/', views.export_customer_statement, name='export-statement'),
    path('<int:pk>/record-payment/', views.record_payment, name='record-payment'),

    path('search/', api_views.customer_search_api, name='api_search'),
    path('create-api/', api_views.customer_create_api, name='api_create'),
    path('api/filter/', api_views.customer_filter_api, name='api_filter'),
    path('vendor-payment/<int:pk>/', views.record_vendor_payment, name='record-vendor-payment'),
]
