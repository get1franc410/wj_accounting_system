# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\assets\forms.py

from django import forms
from .models import Asset, AssetMaintenance
from apps.accounts.models import Account

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'name',
            'description',
            'purchase_date',
            'purchase_price',
            'asset_account',
            'accumulated_depreciation_account',
            'depreciation_expense_account',
            'salvage_value',
            'useful_life_years',
            'depreciation_method',
            'estimated_total_units',  # For Units of Production
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter asset name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter asset description'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'salvage_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'useful_life_years': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'estimated_total_units': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'asset_account': forms.Select(attrs={'class': 'form-select'}),
            'accumulated_depreciation_account': forms.Select(attrs={'class': 'form-select'}),
            'depreciation_expense_account': forms.Select(attrs={'class': 'form-select'}),
            'depreciation_method': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if company:
            self.fields['asset_account'].queryset = Account.objects.filter(
                company=company,
                account_type__name='Fixed Asset'
            ).order_by('name')

            self.fields['accumulated_depreciation_account'].queryset = Account.objects.filter(
                company=company,
                account_type__name='Accumulated Depreciation'
            ).order_by('name')

            self.fields['depreciation_expense_account'].queryset = Account.objects.filter(
                company=company,
                account_type__name='Depreciation Expense'
            ).order_by('name')
        else:
            self.fields['asset_account'].queryset = Account.objects.none()
            self.fields['accumulated_depreciation_account'].queryset = Account.objects.none()
            self.fields['depreciation_expense_account'].queryset = Account.objects.none()

        # Set field requirements and help text
        self.fields['estimated_total_units'].required = False
        self.fields['estimated_total_units'].help_text = "Required only for Units of Production method"
        self.fields['depreciation_method'].help_text = "Select the method to calculate depreciation"

    def clean(self):
        cleaned_data = super().clean()
        depreciation_method = cleaned_data.get('depreciation_method')
        estimated_total_units = cleaned_data.get('estimated_total_units')

        # Validate Units of Production method
        if depreciation_method == Asset.DepreciationMethod.UNITS_OF_PRODUCTION:
            if not estimated_total_units or estimated_total_units <= 0:
                raise forms.ValidationError(
                    "Estimated total units is required for Units of Production depreciation method."
                )

        return cleaned_data


class AssetMaintenanceForm(forms.ModelForm):
    # Define asset field at class level so it's always available
    asset = forms.ModelChoiceField(
        queryset=Asset.objects.none(),  # Will be populated in __init__
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Asset",
        required=False  # We'll handle requirement in the view
    )
    
    class Meta:
        model = AssetMaintenance
        fields = ['asset', 'maintenance_date', 'maintenance_type', 'description', 'cost']
        widgets = {
            'maintenance_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'maintenance_type': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'cost': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}
            ),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        hide_asset_field = kwargs.pop('hide_asset_field', False)
        super().__init__(*args, **kwargs)
        
        # Populate asset choices if company is provided
        if company:
            self.fields['asset'].queryset = Asset.objects.filter(company=company).order_by('name')
            if not hide_asset_field:
                self.fields['asset'].required = True
        
        # Hide asset field if requested (when coming from specific asset page)
        if hide_asset_field:
            del self.fields['asset']
