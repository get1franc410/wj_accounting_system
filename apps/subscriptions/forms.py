# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\forms.py
from django import forms
from .models import RegistrationRequest, Subscription

class RegistrationRequestForm(forms.ModelForm):
    """
    Public-facing form for new companies to request a subscription.
    """
    def __init__(self, *args, **kwargs):
        plan_code = kwargs.pop('plan_code', None)
        super().__init__(*args, **kwargs)

        if plan_code == Subscription.Plan.TRIAL:
            self.fields['payment_receipt'].required = False
            self.fields['payment_receipt'].widget = forms.HiddenInput()
        else:
            self.fields['payment_receipt'].required = True

    class Meta:
        model = RegistrationRequest
        # 🎯 MODIFIED: Added new fields
        fields = [
            'company_name', 
            'business_base_country',
            'business_industry',
            'contact_name', 
            'contact_email', 
            'contact_phone', 
            'payment_receipt',
            'notes'
        ]
        # 🎯 MODIFIED: Added widgets for new fields
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Company\'s Full Name'}),
            'business_base_country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Nigeria, United States'}),
            'business_industry': forms.Select(attrs={'class': 'form-select'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Full Name'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your.email@company.com'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Phone Number'}),
            'payment_receipt': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'e.g., "Payment was made by John Doe."'})
        }
        help_texts = {
            'payment_receipt': 'Please upload a clear image or PDF of your payment receipt.',
            'notes': 'Optional: Any additional information for our team.',
            'business_industry': 'Optional: Select the industry that best describes your business.'
        }
