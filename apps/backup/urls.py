# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\backup\urls.py

from django.urls import path
from . import views

app_name = 'backup'

urlpatterns = [
    path('settings/', views.backup_settings_view, name='settings'),
    path('history/', views.backup_history_view, name='history'),
]
