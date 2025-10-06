# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\production\urls.py

from django.urls import path
from . import views

app_name = 'production'

urlpatterns = [
    # Formula URLs
    path('formulas/', views.ProductionFormulaListView.as_view(), name='formula_list'),
    path('formulas/create/', views.ProductionFormulaCreateView.as_view(), name='formula_create'),
    path('formulas/<int:pk>/', views.ProductionFormulaDetailView.as_view(), name='formula_detail'),
    path('formulas/<int:pk>/edit/', views.ProductionFormulaUpdateView.as_view(), name='formula_update'),
    
    # Production Order URLs
    path('orders/', views.ProductionOrderListView.as_view(), name='order_list'),
    path('orders/create/', views.ProductionOrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.ProductionOrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/execute/', views.ProductionOrderExecuteView.as_view(), name='order_execute'),
    path('orders/<int:pk>/cancel/', views.ProductionOrderCancelView.as_view(), name='order_cancel'),
    
    # API Endpoints
    path('api/formulas/<int:pk>/', views.get_formula_details, name='api_formula_details'),
    path('api/calculate-requirements/', views.calculate_production_requirements, name='api_calculate_requirements'),
]
