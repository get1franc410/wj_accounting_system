# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\production\forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import ProductionFormula, FormulaIngredient, ProductionOrder, MaterialUsage
from apps.inventory.models import InventoryItem, InventoryBatch

class ProductionFormulaForm(forms.ModelForm):
    class Meta:
        model = ProductionFormula
        fields = [
            'name', 'finished_product', 'unit_quantity', 'description',
            'labor_cost', 'overhead_cost', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'finished_product': forms.HiddenInput(),
            'unit_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'labor_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'overhead_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['finished_product'].queryset = InventoryItem.objects.filter(
                company=company,
                item_type=InventoryItem.PRODUCT
            ).order_by('name')

class FormulaIngredientForm(forms.ModelForm):
    material_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control material-search-input',
            'placeholder': 'Search materials...'
        })
    )

    class Meta:
        model = FormulaIngredient
        fields = ['material', 'quantity', 'notes']
        widgets = {
            'material': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0.0001'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if company:
            self.fields['material'].queryset = InventoryItem.objects.filter(
                company=company
            ).order_by('name')

        if self.instance and self.instance.pk and self.instance.material:
            self.fields['material_search'].initial = self.instance.material.name
            self.fields['material_search'].widget.attrs['data-initial-name'] = self.instance.material.name
            self.fields['material_search'].widget.attrs['data-initial-unit'] = self.instance.material.unit_of_measurement or ''

        for field in self.fields.values():
            field.label = False

FormulaIngredientFormSet = inlineformset_factory(
    ProductionFormula,
    FormulaIngredient,
    form=FormulaIngredientForm,
    extra=0,
    can_delete=True,
    can_delete_extra=False
)


class ProductionOrderForm(forms.ModelForm):
    class Meta:
        model = ProductionOrder
        fields = [
            'formula', 'quantity', 'planned_date', 'notes'
        ]
        widgets = {
            'formula': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'planned_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            self.fields['formula'].queryset = ProductionFormula.objects.filter(
                company=company,
                is_active=True
            ).order_by('name')


class ProductionOrderExecuteForm(forms.ModelForm):
    class Meta:
        model = ProductionOrder
        fields = ['actual_labor_cost', 'actual_overhead_cost', 'notes']
        widgets = {
            'actual_labor_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'actual_overhead_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class MaterialUsageForm(forms.ModelForm):
    class Meta:
        model = MaterialUsage
        fields = ['material', 'planned_quantity', 'actual_quantity', 'batch', 'notes']
        widgets = {
            'material': forms.HiddenInput(),
            'planned_quantity': forms.HiddenInput(),
            # FIX: Add widgets here to apply classes automatically
            'actual_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'batch': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        material = self.instance.material if self.instance else None

        if 'batch' in self.fields and material and company:
            self.fields['batch'].queryset = InventoryBatch.objects.filter(
                item__company=company,
                item=material,
                quantity_remaining__gt=0
            ).order_by('expiry_date')
            
            self.fields['batch'].label_from_instance = lambda obj: f"{obj.batch_number} (Avail: {obj.quantity_remaining})"
            self.fields['batch'].required = False
            self.fields['batch'].empty_label = "Auto (FIFO)"

        # This correctly pre-fills the 'actual_quantity' input with the planned value
        if 'actual_quantity' in self.fields and self.instance:
            if not self.initial.get('actual_quantity'):
                self.initial['actual_quantity'] = self.instance.planned_quantity


MaterialUsageFormSet = inlineformset_factory(
    ProductionOrder,
    MaterialUsage,
    form=MaterialUsageForm,
    fields=['material', 'planned_quantity', 'actual_quantity', 'batch', 'notes'],
    extra=0,
    can_delete=False
)
