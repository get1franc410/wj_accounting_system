# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\config\urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView 

# Import the API views directly
from apps.customers import api_views as customer_api
from apps.inventory import api_views as inventory_api
from apps.transactions import api_views as transaction_api

urlpatterns = [
    # <<< CHANGED >>> The 'core' app now handles the root URL for the public landing page.
    path('', include('apps.core.urls', namespace='core')),
    
    # <<< MOVED >>> The dashboard is now at its own dedicated URL.
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),

    # Your other app URLs
    path('admin/', admin.site.urls),
    path('accounts/', include(('apps.authentication.urls', 'apps.authentication'), namespace='auth')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('journal/', include('apps.journal.urls', namespace='journal')), 
    path('reporting/', include('apps.reporting.urls', namespace='reporting')),
    path('customers/', include('apps.customers.urls', namespace='customers')),
    path('inventory/', include('apps.inventory.urls', namespace='inventory')),
    path('transactions/', include('apps.transactions.urls', namespace='transactions')),
    path('assets/', include('apps.assets.urls', namespace='assets')),
    path('backup/', include('apps.backup.urls', namespace='backup')),
    path('subscriptions/', include('apps.subscriptions.urls', namespace='subscriptions')),

    # API URLs
    path('api/customers/search/', customer_api.customer_search_api, name='api_customer_search'),
    path('api/customers/create-api/', customer_api.customer_create_api, name='api_customer_create'),
    path('api/inventory/items/search/', inventory_api.inventory_search_api, name='api_inventory_search'),
    path('api/inventory/items/<int:item_id>/', inventory_api.inventory_item_detail_api, name='api_inventory_detail'),
    path('api/transactions/search/', transaction_api.transaction_search_api, name='api_transaction_search'),

    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'assets/img/favicon.png', permanent=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
