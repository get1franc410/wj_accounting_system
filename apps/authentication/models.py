# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\authentication\models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import Company

class User(AbstractUser):
    """
    Custom user model that is company-centric and includes user roles.
    """
    class UserType(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrator')
        ACCOUNTANT = 'ACCOUNTANT', _('Accountant')
        MANAGER = 'MANAGER', _('Manager')
        STOCK_KEEPER = 'STOCK_KEEPER', _('Stock Keeper') 
        AUDITOR = 'AUDITOR', _('External Auditor')    
        VIEWER = 'VIEWER', _('Viewer')

    # The company this user belongs to. This is the key to our company-centric design.
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='users',
        null=True, # Allows superuser creation without a company
        blank=True
    )

    # Role within the company
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.VIEWER
    )

    # Feature Flags
    is_super_admin = models.BooleanField(
        default=False,
        help_text=_('Designates this user as the company\'s main administrator.')
    )
    force_password_change = models.BooleanField(
        default=True,
        help_text=_('If True, the user must change their password on next login.')
    )
    
    last_active = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username
