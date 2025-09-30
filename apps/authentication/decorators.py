# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\authentication\decorators.py

from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import AccessMixin

def user_type_required(allowed_roles=[]):
    """
    Decorator for views that checks that the user is logged in and has a role
    in the list of allowed roles.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                # This will be handled by @login_required, but as a fallback
                raise PermissionDenied

            if request.user.user_type not in allowed_roles:
                # If user's role is not in the allowed list, raise a 403 Forbidden error.
                raise PermissionDenied
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

class RoleRequiredMixin(AccessMixin):
    """
    Mixin for Class-Based Views to check for user roles.
    """
    allowed_roles = [] # Define this in your CBV

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.user_type not in self.allowed_roles:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

