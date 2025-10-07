# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\transactions\forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import Transaction, TransactionItem, TransactionCategory
from .constants import TransactionType  # 🎯 CENTRALIZED TYPES
from apps.inventory.models import InventoryItem
from apps.customers.models import Customer
from django.forms.widgets import Select
from apps.accounts.models import Account, AccountType
from .models import ExpenseLine

class ItemSelectWidget(forms.Select):
    """
    Custom widget to add data attributes for prices and description to each item option.
    This allows JavaScript to easily grab the correct data.
    """
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
        # Handle different value types properly
        if value:
            try:
                # Extract the actual value if it's a ModelChoiceIteratorValue
                if hasattr(value, 'value'):
                    actual_value = value.value
                else:
                    actual_value = value
                
                # Only query if we have a valid integer value
                if actual_value and actual_value != '':
                    item = InventoryItem.objects.get(pk=actual_value)
                    option['attrs']['data-sale-price'] = str(item.sale_price)
                    option['attrs']['data-purchase-price'] = str(item.purchase_price)
                    option['attrs']['data-description'] = item.description or ''
            except (InventoryItem.DoesNotExist, ValueError, TypeError):
                # If item doesn't exist or value is invalid, just skip adding data attributes
                pass
                
        return option

class TransactionCategoryForm(forms.ModelForm):
    # 🎯 CENTRALIZED TRANSACTION TYPE CHOICES
    allowed_transaction_types = forms.MultipleChoiceField(
        choices=TransactionType.CHOICES,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select which transaction types can use this category",
        required=False  # Add this to prevent validation issues
    )
    
    class Meta:
        model = TransactionCategory
        fields = ['name', 'account_type', 'allowed_transaction_types', 'default_account', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if self.company:
            # 🔧 FIX: Get account types that have accounts in this company
            self.fields['account_type'].queryset = AccountType.objects.filter(
                accounts__company=self.company  # ✅ CORRECT FIELD NAME
            ).distinct().order_by('category', 'name')
            
            # 🎯 DYNAMIC ACCOUNTS - Grouped by account type for better UX
            accounts = Account.objects.filter(
                company=self.company
            ).select_related('account_type').order_by('account_type__name', 'account_number')
            
            self.fields['default_account'].queryset = accounts
            
            # Group accounts by account type for better display
            account_choices = [('', '---------')]
            current_type = None
            for acc in accounts:
                if current_type != acc.account_type.name:
                    if current_type is not None:
                        account_choices.append(('', '─────────'))  # Separator
                    current_type = acc.account_type.name
                
                account_choices.append((
                    acc.id, 
                    f"{acc.account_number} - {acc.name} ({acc.account_type.name})"
                ))
            
            self.fields['default_account'].widget = forms.Select(choices=account_choices)
        
        # Add JavaScript for dynamic account filtering
        self.fields['account_type'].widget.attrs.update({
            'onchange': 'filterAccountsByType(this.value)',
            'class': 'form-select'
        })
    
    def clean(self):
        """Enhanced validation with centralized transaction types"""
        cleaned_data = super().clean()
        account_type = cleaned_data.get('account_type')
        default_account = cleaned_data.get('default_account')
        allowed_transaction_types = cleaned_data.get('allowed_transaction_types')
        
        # ✅ VALIDATION 1: Default account must belong to selected account type
        if account_type and default_account:
            if default_account.account_type != account_type:
                raise forms.ValidationError({
                    'default_account': f'Selected account must belong to account type: {account_type.name}'
                })
        
        # ✅ VALIDATION 2: Smart recommendations using centralized logic
        if account_type and allowed_transaction_types:
            recommended = TransactionType.get_recommended_for_account_category(
                account_type.category
            )
            unusual_types = [t for t in allowed_transaction_types if t not in recommended]
            
            if unusual_types:
                unusual_names = [TransactionType.get_display_name(t) for t in unusual_types]
                recommended_names = [TransactionType.get_display_name(t) for t in recommended]
                
                self.add_error(
                    'allowed_transaction_types',
                    f"Note: {', '.join(unusual_names)} are unusual for {account_type.get_category_display()} accounts. "
                    f"Recommended types: {', '.join(recommended_names)}"
                )
        
        # ✅ VALIDATION 3: At least one transaction type must be selected
        if not allowed_transaction_types:
            raise forms.ValidationError({
                'allowed_transaction_types': 'Please select at least one transaction type.'
            })
        
        return cleaned_data

class TransactionForm(forms.ModelForm):
    # A visible text input for the user to type their search query
    customer_search = forms.CharField(
        label="Customer / Vendor",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control smart-search-input',
            'placeholder': 'Search customers or vendors...'
        })
    )

    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    due_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), required=False)
    paid_in_full = forms.BooleanField(
        required=False,
        label="Paid in full",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    use_line_items = forms.BooleanField(
        required=False,
        label="Use Line Items (Products/Services)",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    manual_total_amount = forms.DecimalField(
        max_digits=15, decimal_places=2, required=False,
        label="Total Amount",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    class Meta:
        model = Transaction
        fields = [
            'transaction_type', 'customer', 'category', 'date', 'due_date',
            'reference_number', 'description', 'attachment', 'use_line_items',
            'manual_total_amount', 'amount_paid', 'paid_in_full'
        ]
        widgets = {
            'customer': forms.HiddenInput(),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_transaction_type'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Add the original 'customer' field back, but as a hidden input to store the ID
        self.fields['customer'] = forms.ModelChoiceField(
            queryset=Customer.objects.filter(company=company),
            widget=forms.HiddenInput(),
            required=False
        )

        # Set initial state for the 'use_line_items' checkbox
        if self.instance and self.instance.pk:
            self.fields['use_line_items'].initial = self.instance.items.exists()
            if not self.instance.items.exists():
                self.fields['manual_total_amount'].initial = self.instance.total_amount
        elif self.data:
            self.fields['use_line_items'].initial = self.data.get('use_line_items') == 'on'
        else:
            self.fields['use_line_items'].initial = True

        if company:
            transaction_type = self.data.get('transaction_type') if self.data else (self.instance.transaction_type if self.instance.pk else None)
            
            # If editing an existing transaction, populate the search field with the customer's name
            if self.instance and self.instance.pk and self.instance.customer:
                self.fields['customer_search'].initial = self.instance.customer.name
                self.fields['customer'].initial = self.instance.customer.id

            # Category filtering logic remains the same
            categories = TransactionCategory.objects.filter(company=company)
            if transaction_type:
                all_categories = list(categories)
                compatible_categories = [cat for cat in all_categories if transaction_type in cat.allowed_transaction_types]
                category_ids = [cat.id for cat in compatible_categories]
                categories = TransactionCategory.objects.filter(id__in=category_ids)
            
            self.fields['category'].queryset = categories.order_by('name')
        
        # Re-order fields to place the search input correctly
        self.order_fields(field_order=[
            'transaction_type', 'customer_search', 'customer', 'date', 'due_date', 'reference_number', 
            'category', 'description', 'attachment',
            'use_line_items', 'manual_total_amount', 
            'amount_paid', 'paid_in_full'
        ])

    def clean(self):
        # No changes needed in the clean method, it remains the same
        cleaned_data = super().clean()
        use_line_items = cleaned_data.get('use_line_items')
        transaction_type = cleaned_data.get('transaction_type')
    
        is_simple_transaction = not use_line_items

        if is_simple_transaction:
            category = cleaned_data.get('category')
            total_amount = cleaned_data.get('manual_total_amount')
            
            if transaction_type:
                type_display = TransactionType.get_display_name(transaction_type)
                if not category and not self.data.get('expense_lines-TOTAL_FORMS'):
                    self.add_error('category', f'A category is required for simple {type_display.lower()}s.')
                
                if not total_amount or total_amount <= 0:
                    pass
        
        return cleaned_data

class ExpenseLineForm(forms.ModelForm):
    """
    Form for a single expense split line.
    """
    class Meta:
        model = ExpenseLine
        fields = ['account', 'amount', 'description']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control expense-amount', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['account'].queryset = Account.objects.filter(
                company=company,
                account_type__category__in=[AccountType.Category.ASSET, AccountType.Category.EXPENSE]
            ).order_by('account_number')
        
        for field in self.fields.values():
            field.label = False

ExpenseLineFormSet = inlineformset_factory(
    Transaction,
    ExpenseLine,
    form=ExpenseLineForm,
    extra=1,
    can_delete=True,
    can_delete_extra=True
)

class TransactionItemForm(forms.ModelForm):
    # A visible text input for searching inventory items
    item_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control item-search-input', 
            'placeholder': 'Search products...' # Changed placeholder for consistency
        }),
    )

    class Meta:
        model = TransactionItem
        fields = ['item', 'description', 'quantity', 'unit_price']
        widgets = {
            'item': forms.HiddenInput(),
            'description': forms.TextInput(attrs={
                'class': 'form-control line-description',
                'placeholder': 'Overrides the default item description if needed.' # Added placeholder
            }),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity', 'step': '0.01', 'placeholder': '1.00'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control unit-price', 'step': '0.01', 'placeholder': 'Price per unit.'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if company:
            self.fields['item'].queryset = InventoryItem.objects.filter(company=company)
        
        # Make item field not required at form level
        self.fields['item'].required = False
        
        # Set initial values for search field if editing
        if self.instance and self.instance.pk and self.instance.item:
            self.fields['item_search'].initial = self.instance.item.name
            self.fields['item'].initial = self.instance.item.id

        # --- ✅ CORRECTED LOGIC ---
        # Remove labels for ALL fields for a clean inline display in the table.
        for field in self.fields.values():
            field.label = False

    def has_changed(self):
        """
        Override to check if form has any real data.
        This prevents empty rows from being processed.
        """
        # Check if any meaningful data has been entered
        if self.data:
            item = self.data.get(self.add_prefix('item'))
            quantity = self.data.get(self.add_prefix('quantity'))
            unit_price = self.data.get(self.add_prefix('unit_price'))
            
            # If there's no item and no other data, consider it unchanged
            if not item and not quantity and not unit_price:
                return False
        
        return super().has_changed()

    def clean(self):
        """
        Enhanced validation to prevent the NOT NULL constraint error
        """
        cleaned_data = super().clean()
        
        # If the form is marked for deletion, skip validation
        if cleaned_data.get('DELETE'):
            return cleaned_data
        
        item = cleaned_data.get('item')
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')
        description = cleaned_data.get('description')
        
        # Check if the row has any data at all
        has_any_data = any([item, quantity, unit_price, description])
        
        if has_any_data:
            # If there's any data, item is required
            if not item:
                # We raise the error on item_search as it's the visible field
                self.add_error('item_search', "Please select an item or clear this row completely.")
            
            # Validate quantity
            if not quantity or quantity <= 0:
                self.add_error('quantity', 'Quantity must be > 0.')
            
            # Validate unit price
            if unit_price is None or unit_price < 0:
                self.add_error('unit_price', 'Price cannot be negative.')
        
        return cleaned_data
    
TransactionItemFormSet = inlineformset_factory(
    Transaction,
    TransactionItem,
    form=TransactionItemForm,
    extra=1,
    can_delete=True,
    can_delete_extra=True
)