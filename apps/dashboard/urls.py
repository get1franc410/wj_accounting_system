# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\dashboard\urls.py

from django.urls import path
from .views import dashboard_home

app_name = 'dashboard'

urlpatterns = [
    # This makes the dashboard the homepage of the entire site
    path('', dashboard_home, name='home'),
]
