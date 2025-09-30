# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\authentication\admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Admin configuration for the custom User model.
    """
    # Add our custom fields to the display list
    list_display = ('username', 'email', 'company', 'user_type', 'is_staff')
    list_filter = ('company', 'user_type', 'is_staff', 'is_superuser', 'is_active')

    # Add our custom fields to the fieldsets for the user detail/edit page
    # This adds a new section called "Company & Role"
    fieldsets = UserAdmin.fieldsets + (
        ('Company & Role', {
            'fields': ('company', 'user_type', 'is_super_admin', 'force_password_change'),
        }),
    )

    # Add our custom fields to the add-user form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Company & Role', {
            'fields': ('company', 'user_type', 'is_super_admin', 'force_password_change'),
        }),
    )
