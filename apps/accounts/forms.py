# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\accounts\forms.py

from django import forms
from .models import Account, AccountType

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            'name', 'account_number', 'account_type', 'parent', 
            'description', 'is_control_account', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # We must receive the company object from the view
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if not company:
            # If there's no company, this form is not usable.
            # You might want to raise an error or handle this case as needed.
            return

        # Filter the 'parent' account choices to only show accounts from the user's company.
        # This is crucial for data integrity in a multi-company setup.
        self.fields['parent'].queryset = Account.objects.filter(company=company).order_by('account_number')
        
        # You can also set the queryset for account_type if needed, but it's usually global.
        self.fields['account_type'].queryset = AccountType.objects.all()

