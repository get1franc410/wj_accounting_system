# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\assets\urls.py

from django.urls import path
from .views import (
    AssetListView,
    AssetDetailView,
    AssetCreateView,
    AssetUpdateView,
    AssetDeleteView,
    AddMaintenanceView,
    MaintenanceListView,
)
from . import views

app_name = 'assets'

urlpatterns = [
    path('', AssetListView.as_view(), name='asset-list'),
    path('new/', AssetCreateView.as_view(), name='asset-create'),
    path('<int:pk>/', AssetDetailView.as_view(), name='asset-detail'),
    path('<int:pk>/edit/', AssetUpdateView.as_view(), name='asset-update'),
    path('<int:pk>/delete/', AssetDeleteView.as_view(), name='asset-delete'),
    
    # Maintenance URLs - Fixed patterns
    path('maintenance/', MaintenanceListView.as_view(), name='maintenance-list'),
    path('maintenance/new/', AddMaintenanceView.as_view(), {'asset_pk': 0}, name='maintenance-create'),
    path('<int:asset_pk>/maintenance/add/', AddMaintenanceView.as_view(), name='add-maintenance'),

    # Export URLs
    path('export/', views.export_assets, name='export'),
    path('export/maintenance/', views.export_maintenance_records, name='export-maintenance'),
    path('export/depreciation/', views.export_depreciation_schedule, name='export-depreciation'),
]
