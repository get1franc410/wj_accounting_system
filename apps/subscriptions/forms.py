# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\subscriptions\forms.py
from django import forms
from .models import RegistrationRequest, Subscription

class RegistrationRequestForm(forms.ModelForm):
    """
    Public-facing form for new companies to request a subscription.
    The 'plan' is set in the view. This form is now dynamic.
    """
    def __init__(self, *args, **kwargs):
        # --- NEW: Get the plan_code passed from the view ---
        plan_code = kwargs.pop('plan_code', None)
        super().__init__(*args, **kwargs)

        # --- NEW: Conditional logic for the Trial plan ---
        if plan_code == Subscription.Plan.TRIAL:
            # For trials, the payment receipt is not needed
            self.fields['payment_receipt'].required = False
            self.fields['payment_receipt'].widget = forms.HiddenInput() # Hide the field from the user
        else:
            # For all other plans, it is mandatory
            self.fields['payment_receipt'].required = True

    class Meta:
        model = RegistrationRequest
        fields = [
            'company_name', 
            'contact_name', 
            'contact_email', 
            'contact_phone', 
            'payment_receipt',
            'notes'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Company\'s Full Name'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Full Name'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email Address'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Phone Number'}),
            'payment_receipt': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'e.g., "Payment was made by John Doe."'})
        }
        help_texts = {
            'payment_receipt': 'Please upload a clear image or PDF of your payment receipt.',
            'notes': 'Optional: Any additional information for our team.'
        }