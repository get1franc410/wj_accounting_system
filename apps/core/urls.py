# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\urls.py

from django.urls import path
# <<< REMOVED >>> No longer need DashboardView here, it's in the dashboard app
from . import views

app_name = 'core'

urlpatterns = [
    # This is now the main public landing page for the entire site.
    path('', views.public_home_view, name='public_home'),
    
    # <<< REMOVED CONFLICT >>> The line below was conflicting and has been removed.
    # path('', DashboardView.as_view(), name='dashboard'),
    
    # All other core URLs remain the same
    path('settings/', views.settings_dashboard, name='settings_dashboard'),
    
    # Admin control panel
    path('admin-settings/', views.admin_settings, name='admin_settings'),
    path('user-management/', views.user_management, name='user_management'),
    path('database-config/', views.database_config, name='database_config'),
    
    # User profile and personal settings
    path('profile/', views.user_profile, name='user_profile'),
    
    # Category management
    path('add-category/', views.add_category, name='add_category'),
    path('edit-category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('get-category/<int:category_id>/', views.get_category, name='get_category'),
    
    # Instant actions
    path('instant-backup/', views.instant_backup, name='instant_backup'),
    path('send-instant-reminders/', views.send_instant_reminders, name='send_instant_reminders'),
    path('send-audit-reminder/', views.send_audit_reminder, name='send_audit_reminder'),
    path('send-audit-documents/', views.send_audit_documents, name='send_audit_documents'),
    path('test-email-config/', views.test_email_config, name='test_email_config'),
    path('run-maintenance/', views.run_maintenance, name='run_maintenance'),
    
    # User management actions
    path('create-user/', views.create_user, name='create_user'),
    path('update-user/<int:user_id>/', views.update_user, name='update_user'),
    path('get-user/<int:user_id>/', views.get_user, name='get_user'),
    path('deactivate-user/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
]
