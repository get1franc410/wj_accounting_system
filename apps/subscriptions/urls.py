# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\urls.py
from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # The main entry point, showing plans and payment info.
    # This now uses subscription_plans_view.
    path('register/', views.subscription_plans_view, name='register'),
    
    # The page with the actual registration form, linked from the plans page.
    # This uses subscription_register_view.
    path('register/form/<str:plan_code>/', views.subscription_register_view, name='register_form'),
    
    # URL for users to check their subscription status
    path('status/', views.subscription_status, name='status'),
]
