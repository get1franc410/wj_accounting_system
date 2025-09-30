# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\inventory\forms.py

from django import forms
from django.utils import timezone
from .models import InventoryItem, InventoryTransaction, InventoryBatch, InventoryMovement, InventoryPriceAdjustment
from apps.accounts.models import Account

class InventoryItemForm(forms.ModelForm):
    # Add a custom field for initial purchase price when creating new items
    initial_purchase_price = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False,
        label="Initial Purchase Price",
        help_text="Cost per unit for initial stock (will create a cost layer)"
    )

    expiry_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Expiry Date",
        help_text="Set expiry date for perishable items (only if expiry tracking is enabled)"
    )
    
    class Meta:
        model = InventoryItem
        fields = [
            'name', 'sku', 'item_type', 'unit_of_measurement', 'description',
            'sale_price', 'reorder_level', 'costing_method',
            'enable_batch_tracking', 'allow_fractional_quantities', 'track_expiry',
            'expiry_date',
            'income_account', 'expense_account', 'asset_account'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'enable_batch_tracking': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-toggle': 'batch-options'
            }),
            'allow_fractional_quantities': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'track_expiry': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-toggle': 'expiry-options'  
            }),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), 
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            if not self.instance.track_expiry:
                self.fields['expiry_date'].widget.attrs['style'] = 'display: none;'

        # Enhanced unit choices with smart categorization
        unit_choices = []
        for category, units in InventoryItem.UNIT_CATEGORIES.items():
            category_choices = [(unit, dict(InventoryItem.UNIT_CHOICES)[unit]) 
                              for unit in units if unit in dict(InventoryItem.UNIT_CHOICES)]
            if category_choices:
                unit_choices.append((category.title(), category_choices))
        
        self.fields['unit_of_measurement'].choices = unit_choices

        # Show current average cost for existing items
        if self.instance and self.instance.pk:
            self.fields['current_average_cost'] = forms.DecimalField(
                label="Current Average Cost",
                initial=self.instance.current_average_cost,
                disabled=True,
                required=False,
                help_text="Calculated from cost layers/batches"
            )
            self.fields['quantity_on_hand'] = forms.DecimalField(
                label="Current Quantity on Hand",
                initial=self.instance.quantity_on_hand,
                disabled=True,
                required=False,
                help_text="Updated automatically by inventory transactions"
            )
            
            # Show batch and expiry info for existing items
            if self.instance.enable_batch_tracking:
                active_batches = self.instance.batches.filter(quantity_remaining__gt=0).count()
                self.fields['active_batches_info'] = forms.CharField(
                    label="Active Batches",
                    initial=f"{active_batches} active batch(es)",
                    disabled=True,
                    required=False
                )
            
            # Reorder fields for better display
            new_order = list(self.fields.keys())
            if 'current_average_cost' in new_order:
                new_order.insert(-4, new_order.pop(new_order.index('current_average_cost')))
            if 'quantity_on_hand' in new_order:
                new_order.insert(-4, new_order.pop(new_order.index('quantity_on_hand')))
            self.order_fields(new_order)
        else:
            # For new items, show initial purchase price field
            new_order = list(self.fields.keys())
            new_order.insert(-4, new_order.pop(new_order.index('initial_purchase_price')))
            self.order_fields(new_order)

        if company:
            self.fields['income_account'].queryset = Account.objects.filter(
                company=company, account_type__name='Revenue'
            )
            self.fields['expense_account'].queryset = Account.objects.filter(
                company=company, account_type__name__in=['Expense', 'Cost of Goods Sold']
            )
            self.fields['asset_account'].queryset = Account.objects.filter(
                company=company, account_type__name='Current Asset'
            )

    def clean(self):
        cleaned_data = super().clean()
        enable_batch_tracking = cleaned_data.get('enable_batch_tracking')
        costing_method = cleaned_data.get('costing_method')
        track_expiry = cleaned_data.get('track_expiry')
        expiry_date = cleaned_data.get('expiry_date')

        # 🆕 VALIDATE EXPIRY DATE
        if track_expiry and not expiry_date:
            self.add_error('expiry_date', 'Expiry date is required when expiry tracking is enabled.')
        
        # Auto-set costing method for batch tracking
        if enable_batch_tracking and costing_method != InventoryItem.CostingMethod.SPECIFIC_ID:
            cleaned_data['costing_method'] = InventoryItem.CostingMethod.SPECIFIC_ID
            self.add_error('costing_method', 
                'Costing method automatically set to "Specific Identification" for batch tracking.')
        
        return cleaned_data

class InventoryPriceAdjustmentForm(forms.ModelForm):
    class Meta:
        model = InventoryPriceAdjustment
        fields = ['new_unit_cost', 'quantity_affected', 'adjustment_reason', 'reference']
        widgets = {
            'adjustment_reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'new_unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantity_affected': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        item = kwargs.pop('item', None)
        super().__init__(*args, **kwargs)
        
        if item:
            self.fields['old_unit_cost'] = forms.DecimalField(
                label="Current Unit Cost",
                initial=item.current_average_cost,
                disabled=True,
                required=False,
                help_text="Current cost before adjustment"
            )
            self.fields['quantity_affected'].initial = item.quantity_on_hand
            
            # Reorder fields
            field_order = ['old_unit_cost', 'new_unit_cost', 'quantity_affected', 'adjustment_reason', 'reference']
            self.order_fields(field_order)
    
    def clean(self):
        cleaned_data = super().clean()
        new_unit_cost = cleaned_data.get('new_unit_cost')
        quantity_affected = cleaned_data.get('quantity_affected')
        
        if new_unit_cost and new_unit_cost < 0:
            raise forms.ValidationError("New unit cost cannot be negative.")
        
        if quantity_affected and quantity_affected <= 0:
            raise forms.ValidationError("Quantity affected must be positive.")
        
        return cleaned_data
    
class InventoryTransactionForm(forms.ModelForm):
    class Meta:
        model = InventoryTransaction
        fields = ['item', 'transaction_type', 'batch', 'quantity', 'unit_cost', 'transaction_date', 'notes']
        widgets = {
            'transaction_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'batch': forms.Select(attrs={'class': 'form-select batch-select', 'style': 'display: none;'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity-input', 'step': '0.01'}),
            # FIX: Added widget for unit_cost to apply consistent styling and ensure JS functionality.
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if company:
            self.fields['item'].queryset = InventoryItem.objects.filter(
                company=company, 
                item_type=InventoryItem.PRODUCT
            ).order_by('name')

        self.fields['transaction_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
        
        # Make unit_cost required for purchase transactions
        self.fields['unit_cost'].help_text = "Required for purchases, sales returns, and opening stock"
        
        # Add batch field help text
        self.fields['batch'].help_text = "Select batch (shown only for batch-tracked items)"
    
    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        unit_cost = cleaned_data.get('unit_cost')
        item = cleaned_data.get('item')
        batch = cleaned_data.get('batch')
        quantity = cleaned_data.get('quantity')
        
        # Require unit_cost for transactions that add inventory
        if transaction_type in [
            InventoryTransaction.PURCHASE, 
            InventoryTransaction.OPENING_STOCK, 
            InventoryTransaction.SALES_RETURN
        ]:
            if not unit_cost or unit_cost <= 0:
                raise forms.ValidationError(
                    f"Unit cost is required for {self.get_transaction_type_display(transaction_type)} transactions"
                )
        
        # Validate batch tracking
        if item and item.enable_batch_tracking:
            if transaction_type in InventoryTransaction.get_stock_decrease_types():
                if not batch:
                    raise forms.ValidationError("Batch selection is required for batch-tracked items.")
                if batch.quantity_remaining < quantity:
                    raise forms.ValidationError(
                        f"Insufficient quantity in batch {batch.batch_number}. "
                        f"Available: {batch.quantity_remaining}"
                    )
        
        # Validate fractional quantities
        if item and not item.allow_fractional_quantities and quantity and quantity % 1 != 0:
            raise forms.ValidationError(
                f"Item '{item.name}' only allows whole number quantities."
            )
        
        return cleaned_data
    
    def get_transaction_type_display(self, transaction_type):
        """Helper method to get display name for transaction type"""
        choices_dict = dict(InventoryTransaction.TRANSACTION_TYPE_CHOICES)
        for group_name, group_choices in choices_dict.items():
            if isinstance(group_choices, (list, tuple)):
                for choice_value, choice_display in group_choices:
                    if choice_value == transaction_type:
                        return choice_display
        return transaction_type


class InventoryBatchForm(forms.ModelForm):
    class Meta:
        model = InventoryBatch
        fields = ['batch_number', 'manufacture_date', 'expiry_date', 'supplier', 'notes']
        widgets = {
            'manufacture_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        manufacture_date = cleaned_data.get('manufacture_date')
        expiry_date = cleaned_data.get('expiry_date')
        
        if manufacture_date and expiry_date and expiry_date <= manufacture_date:
            raise forms.ValidationError("Expiry date must be after manufacture date.")
        
        return cleaned_data


class InventoryMovementForm(forms.ModelForm):
    # 🆕 ADD FAIR MARKET VALUE FIELD
    fair_market_value = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False,
        label="Fair Market Value per Unit",
        help_text="For gifts/donations, returns, or corrections - enter estimated market value per unit"
    )
    
    class Meta:
        model = InventoryMovement
        fields = ['item', 'batch', 'movement_type', 'reason', 'custom_reason', 
                 'quantity', 'fair_market_value', 'reference_document', 'notes']
        widgets = {
            'batch': forms.Select(attrs={'class': 'form-select batch-select', 'style': 'display: none;'}),
            'custom_reason': forms.TextInput(attrs={'class': 'form-control', 'style': 'display: none;'}),
            'fair_market_value': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01', 
                'style': 'display: none;'
            }),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity-input', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            self.fields['item'].queryset = InventoryItem.objects.filter(
                company=company, 
                item_type=InventoryItem.PRODUCT
            ).order_by('name')
    
    def clean(self):
        cleaned_data = super().clean()
        reason = cleaned_data.get('reason')
        custom_reason = cleaned_data.get('custom_reason')
        fair_market_value = cleaned_data.get('fair_market_value')
        movement_type = cleaned_data.get('movement_type')
        item = cleaned_data.get('item')
        quantity = cleaned_data.get('quantity')
        batch = cleaned_data.get('batch')
        
        # 🆕 REQUIRE FAIR MARKET VALUE FOR SPECIFIC STOCK-IN MOVEMENTS
        if movement_type == 'IN' and reason in InventoryMovement.FAIR_VALUE_REQUIRED_REASONS:
            if not fair_market_value or fair_market_value <= 0:
                reason_display = dict(InventoryMovement.MOVEMENT_REASONS)[reason]
                raise forms.ValidationError(
                    f"Fair market value is required for '{reason_display}' stock-in movements "
                    f"to maintain accurate inventory valuation."
                )
        
        if reason == 'CUSTOM' and not custom_reason:
            raise forms.ValidationError("Custom reason is required when 'Other' is selected.")
        
        # Validate fractional quantities
        if item and not item.allow_fractional_quantities and quantity and quantity % 1 != 0:
            raise forms.ValidationError(
                f"Item '{item.name}' only allows whole number quantities."
            )
        
        # Validate batch tracking
        if item and item.enable_batch_tracking and not batch:
            raise forms.ValidationError("Batch selection is required for batch-tracked items.")
        
        # Validate stock out movements
        if movement_type == 'OUT' and item:
            if item.enable_batch_tracking and batch:
                if batch.quantity_remaining < quantity:
                    raise forms.ValidationError(
                        f"Insufficient quantity in batch {batch.batch_number}. "
                        f"Available: {batch.quantity_remaining}"
                    )
            elif item.quantity_on_hand < quantity:
                raise forms.ValidationError(
                    f"Insufficient stock. Available: {item.quantity_on_hand}"
                )
        
        return cleaned_data
    
# Enhanced Item Selection Form for Transaction Line Items
class SmartItemSelectionForm(forms.Form):
    """Form for smart item selection in transactions"""
    item = forms.ModelChoiceField(
        queryset=InventoryItem.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select item-select',
            'data-smart-selection': 'true'
        })
    )
    batch = forms.ModelChoiceField(
        queryset=InventoryBatch.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select batch-select',
            'style': 'display: none;'
        })
    )
    quantity = forms.DecimalField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control quantity-input',
            'step': '0.01'
        })
    )
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            self.fields['item'].queryset = InventoryItem.objects.filter(
                company=company
            ).order_by('name')
