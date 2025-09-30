# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\journal\forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import JournalEntry, JournalEntryLine
from apps.accounts.models import Account
from apps.core.models import Company

class JournalEntryForm(forms.ModelForm):
    """
    Form for the main Journal Entry details (date and description).
    """
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    
    class Meta:
        model = JournalEntry
        fields = ['date', 'description']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter a brief description for the entry'}),
        }

class JournalEntryLineForm(forms.ModelForm):
    """
    Form for a single line within a Journal Entry.
    """
    # We filter the account queryset to only show accounts for the user's company
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(), # Initially empty, will be set in the view
        widget=forms.Select(attrs={'class': 'form-control account-select'})
    )

    class Meta:
        model = JournalEntryLine
        fields = ['account', 'debit', 'credit']
        widgets = {
            'debit': forms.NumberInput(attrs={'class': 'form-control debit', 'step': '0.01'}),
            'credit': forms.NumberInput(attrs={'class': 'form-control credit', 'step': '0.01'}),
        }

# This factory creates a set of JournalEntryLineForms linked to a single JournalEntry
JournalEntryLineFormSet = inlineformset_factory(
    JournalEntry,          # Parent model
    JournalEntryLine,      # Child model
    form=JournalEntryLineForm,
    extra=2,               # Start with 2 empty forms
    can_delete=True,       # Allow deleting lines
    min_num=2,             # Require at least 2 lines for a valid entry
    validate_min=True,
)
