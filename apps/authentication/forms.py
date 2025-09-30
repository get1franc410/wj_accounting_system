# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\authentication\forms.py

from django import forms
from django.contrib.auth.forms import SetPasswordForm

class LoginForm(forms.Form):
    """
    A simple form for user authentication.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

class ForcePasswordChangeForm(SetPasswordForm):
    """
    A form that lets a user change their password without entering the old one.
    This inherits from Django's SetPasswordForm to handle validation and hashing.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'New Password'})
        self.fields['new_password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm New Password'})