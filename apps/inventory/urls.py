# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\inventory\urls.py

from django.urls import path
from . import views, api_views

app_name = 'inventory'

urlpatterns = [
    # Main inventory views
    path('', views.InventoryItemListView.as_view(), name='item_list'),
    path('items/<int:pk>/', views.item_detail, name='item_detail'),
    path('items/create/', views.item_create, name='item_create'),
    path('items/<int:pk>/update/', views.item_update, name='item_update'),
    
    # Inventory transactions
    path('transactions/create/', views.InventoryTransactionCreateView.as_view(), name='transaction_create'),
    
    # NEW: Inventory movements
    path('movements/', views.inventory_movement_list, name='movement_list'),
    path('movements/create/', views.inventory_movement_create, name='movement_create'),
    
    # NEW: Batch management
    path('items/<int:item_id>/batches/', views.batch_list, name='batch_list'),
    path('items/<int:item_id>/batches/create/', views.batch_create, name='batch_create'),

    path('items/<int:item_id>/price-adjustment/', views.price_adjustment_create, name='price_adjustment_create'),

    path('api/items/search/', api_views.inventory_search_api, name='inventory_search_api'),
    
    # AJAX endpoints
    path('api/items/<int:item_id>/details/', api_views.inventory_item_detail_api, name='api_item_detail'),
    path('ajax/item/<int:pk>/', views.get_item_details, name='get_item_details'),
    path('ajax/batches/<int:item_id>/', views.get_batch_details, name='get_batch_details'),
    path('ajax/validate-quantity/<int:item_id>/', views.validate_quantity, name='validate_quantity'),
    
    # Export URLs
    path('export/items/', views.export_inventory_items, name='export-items'),
    path('export/transactions/', views.export_inventory_transactions, name='export-transactions'),
    path('export/valuation/', views.export_inventory_valuation, name='export-valuation'),
    path('export/movements/', views.export_inventory_movements, name='export-movements'),

    path('api/items/search/', api_views.inventory_search_api, name='api_items_search'),
    path('items/<int:item_id>/', api_views.inventory_item_detail_api, name='api_item_detail'),
]
