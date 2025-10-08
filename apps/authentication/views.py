# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\authentication\views.py

from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
# Import the new form
from .forms import LoginForm, ForcePasswordChangeForm

def login_view(request):
    """
    Handles user login.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if not user.is_active:
                    messages.error(request, 'This account is inactive. Please contact your administrator.')
                    return render(request, 'authentication/login.html', {'form': form})
                
                login(request, user)
                if user.force_password_change:
                    messages.warning(request, 'You must change your password before you can continue.')
                    return redirect('auth:change_password')
                
                return redirect('dashboard:home')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    # Add a link to the new registration page in the context
    context = {
        'form': form,
        'registration_url': reverse_lazy('subscriptions:register') 
    }
    return render(request, 'authentication/login.html', context)

# --- NEW VIEW ---
@login_required
def change_password_view(request):
    """
    Handles the mandatory password change for a user.
    """
    if request.method == 'POST':
        form = ForcePasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # After saving the new password, we must update the user's session
            # to prevent them from being logged out.
            update_session_auth_hash(request, user)
            
            # Unset the flag
            user.force_password_change = False
            user.save()

            messages.success(request, 'Your password has been changed successfully. You can now access the dashboard.')
            return redirect('dashboard:home')
    else:
        form = ForcePasswordChangeForm(user=request.user)
        
    return render(request, 'authentication/change_password.html', {'form': form})


def logout_view(request):
    """
    Handles user logout.
    """
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('core:public_home')
