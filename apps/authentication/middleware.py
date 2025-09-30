# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\authentication\middleware.py

from django.shortcuts import redirect
from django.urls import reverse

class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # The user must be authenticated to check the flag
        if request.user.is_authenticated and request.user.force_password_change:
            # Allow access to the password change page and the logout page
            allowed_paths = [
                reverse('auth:change_password'),
                reverse('auth:logout')
            ]
            if request.path not in allowed_paths:
                # If they are trying to access any other page, redirect them.
                return redirect('auth:change_password')
        
        response = self.get_response(request)
        return response

