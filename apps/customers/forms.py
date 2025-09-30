# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\customers\forms.py

from django import forms
from .models import Customer

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'name', 
            'entity_type', 
            'email', 
            'phone', 
            'address', 
            'credit_limit'
        ]

    def __init__(self, *args, **kwargs):
        # We need to get the company from the view to validate uniqueness
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        query = Customer.objects.filter(company=self.company, name__iexact=name)
        
        # If we are in "update" mode, exclude the current instance from the check
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
            
        if query.exists():
            raise forms.ValidationError("A customer or vendor with this name already exists for your company.")
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Email is optional, so only validate if it's provided
        if email:
            query = Customer.objects.filter(company=self.company, email__iexact=email)
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            
            if query.exists():
                raise forms.ValidationError("A customer or vendor with this email already exists for your company.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Phone is optional, so only validate if it's provided
        if phone:
            query = Customer.objects.filter(company=self.company, phone=phone)
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                raise forms.ValidationError("A customer or vendor with this phone number already exists for your company.")
        return phone
