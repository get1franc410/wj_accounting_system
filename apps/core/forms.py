# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from apps.authentication.models import User
from .models import Company, EmailConfiguration

class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'industry', 'registration_number', 'tax_number',
            'address', 'phone', 'email', 'website', 'logo',
            'currency', 'fiscal_year_start'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'fiscal_year_start': forms.DateInput(attrs={'type': 'date'}),
        }

class CompanyCurrencyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['currency', 'fiscal_year_start']
        widgets = {
            'fiscal_year_start': forms.DateInput(attrs={'type': 'date'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].help_text = "Select the primary currency for all financial reporting. This will change the symbol (e.g., $, ₦) across the entire application."

class EmailConfigForm(forms.ModelForm):
    app_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Gmail App Password'}),
        help_text="Use Gmail App Password for security. <a href='https://support.google.com/accounts/answer/185833' target='_blank'>Learn how to create one</a>",
        required=False,
        label="App Password"
    )
    
    class Meta:
        model = EmailConfiguration
        fields = ['email_address', 'app_password', 'is_active']
        widgets = {
            'email_address': forms.EmailInput(attrs={'placeholder': 'your-email@gmail.com'}),
        }
        help_texts = {
            'email_address': 'This email will be used to send system notifications.',
            'is_active': 'Enable this configuration to start sending emails.',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.app_password:
            self.fields['app_password'].help_text += " (Leave blank to keep current password)"
            self.fields['app_password'].required = False

class AuditorCompanyForm(forms.ModelForm):
    """Form for managing auditor company information"""
    
    class Meta:
        model = Company
        fields = [
            'name', 'phone', 'email', 'website', 'address',
            'registration_number', 'industry'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'name': forms.TextInput(attrs={'placeholder': 'Auditor Company Name'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Contact Phone Number'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Contact Email Address'}),
            'website': forms.URLInput(attrs={'placeholder': 'Company Website (optional)'}),
            'registration_number': forms.TextInput(attrs={'placeholder': 'Registration Number (optional)'}),
            'industry': forms.TextInput(attrs={'placeholder': 'e.g., Accounting & Auditing'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].help_text = "Name of the external auditing firm"
        self.fields['phone'].help_text = "Primary contact number for the auditing firm"
        self.fields['email'].help_text = "Email address where audit reminders will be sent"
        self.fields['address'].help_text = "Business address of the auditing firm"

class UserCompanyForm(forms.ModelForm):
    """Enhanced form for user company information"""
    
    class Meta:
        model = Company
        fields = [
            'name', 'industry', 'registration_number', 'tax_number',
            'address', 'phone', 'email', 'website', 'logo',
            'currency', 'fiscal_year_start', 'fiscal_closing_grace_period_months'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'fiscal_year_start': forms.DateInput(attrs={'type': 'date'}),
            'name': forms.TextInput(attrs={'placeholder': 'Your Company Name'}),
            'industry': forms.TextInput(attrs={'placeholder': 'e.g., Manufacturing, Retail, Services'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].help_text = "Legal name of your business"
        self.fields['currency'].help_text = "Primary currency for all financial reporting"
        self.fields['fiscal_year_start'].help_text = "Start date of your fiscal year. The end date is calculated automatically."
        self.fields['fiscal_closing_grace_period_months'].help_text = "Months after year-end for accountants to finalize books (e.g., 3)."
        self.fields['tax_number'].help_text = "Tax identification number"

class UserProfileForm(forms.ModelForm):
    """Form for users to update their own profile"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class UserCreationForm(DjangoUserCreationForm):
    """Form for admin to create new users, now with user limit validation."""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    user_type = forms.ChoiceField(choices=User.UserType.choices)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Add CSS classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        """
        Add validation to check if the company has reached its user limit.
        """
        cleaned_data = super().clean()
        
        if self.company:
            try:
                subscription = self.company.subscription
                current_user_count = self.company.users.count()
                
                if current_user_count >= subscription.max_users:
                    raise forms.ValidationError(
                        f"Cannot add new user. Your '{subscription.get_plan_display()}' plan "
                        f"is limited to {subscription.max_users} user(s). "
                        f"Please upgrade your plan to add more users."
                    )
            except self.company._meta.model.subscription.RelatedObjectDoesNotExist:
                 raise forms.ValidationError("Subscription details not found for your company. Please contact support.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.user_type = self.cleaned_data['user_type']
        if self.company:
            user.company = self.company
        if commit:
            user.save()
        return user

class UserUpdateForm(forms.ModelForm):
    """Form for admin to update existing users"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'user_type', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }