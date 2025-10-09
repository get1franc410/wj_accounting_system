# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\inventory\models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.urls import reverse
from apps.core.models import Company
from decimal import Decimal
from django.utils import timezone

class InventoryItem(models.Model):
    STOCK_ITEM = 'stock_item'
    FINISHED_GOOD = 'finished_good'
    SERVICE = 'service'
    ITEM_TYPE_CHOICES = [
        ('Products', (
            (STOCK_ITEM, 'Stock Item'),      
            (FINISHED_GOOD, 'Finished Good'), 
        )),
        (SERVICE, 'Service'),
    ]

    class CostingMethod(models.TextChoices):
        FIFO = 'FIFO', 'First In, First Out'
        LIFO = 'LIFO', 'Last In, First Out'  
        WEIGHTED_AVERAGE = 'WEIGHTED_AVG', 'Weighted Average'
        SPECIFIC_ID = 'SPECIFIC_ID', 'Specific Identification (Batch Tracking)'
        PRICE_ADJUSTMENT = 'PRICE_ADJ', 'Price Adjustment Method'
    
    # Enhanced unit choices with smart categorization
    UNIT_CHOICES = [
        # COUNT Category
        ('Nos', 'Nos (Numbers)'),
        ('pcs', 'Pieces'),
        ('set', 'Set'),
        ('box', 'Box'),
        ('roll', 'Roll'),
        ('bag', 'Bag'),
        
        # WEIGHT Category  
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('ton', 'Tonne'),
        
        # VOLUME Category
        ('litre', 'Litre'),
        ('ml', 'Millilitre'),
        ('m3', 'Cubic Meter'),
        
        # AREA Category
        ('sqm', 'Square Meter'),
        ('m', 'Meter'),
        
        # TIME Category (Services)
        ('per_hour', 'Per Hour'),
        ('per_day', 'Per Day'),
        ('charges', 'Charges'),
        ('per_job', 'Per Job'),
    ]
    
    # Unit categories for smart selection
    UNIT_CATEGORIES = {
        'COUNT': ['Nos', 'pcs', 'set', 'box', 'roll', 'bag'],
        'WEIGHT': ['kg', 'g', 'ton'],
        'VOLUME': ['litre', 'ml', 'm3'],
        'AREA': ['sqm', 'm'],
        'TIME': ['per_hour', 'per_day'],
        'SERVICE': ['charges', 'per_job']
    }

    # Core Fields
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='inventory_items')
    name = models.CharField(max_length=255, help_text="The name of the product or service.")
    sku = models.CharField(max_length=100, blank=True, help_text="Stock Keeping Unit - a unique code for this item.")
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default=STOCK_ITEM)
    description = models.TextField(blank=True)
    
    # Enhanced unit field with expanded choices
    unit_of_measurement = models.CharField(
        max_length=15, 
        choices=UNIT_CHOICES, 
        default='Nos',
        help_text="Unit of measurement for this item"
    )
    
    # Pricing Fields
    sale_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), 
        help_text="The price at which one unit of this item is sold."
    )
    
    # Stock Management
    quantity_on_hand = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), 
        help_text="Current quantity in stock. For 'Product' type items only.", 
        editable=False
    )
    reorder_level = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), 
        help_text="The stock level at which a reorder should be triggered."
    )
    
    # Costing Method
    costing_method = models.CharField(
        max_length=15,
        choices=CostingMethod.choices,
        default=CostingMethod.WEIGHTED_AVERAGE,
        help_text="Method used to calculate cost of goods sold. Use 'Specific Identification' for batch tracking."
    )
    
    # NEW: Enhanced Features
    enable_batch_tracking = models.BooleanField(
        default=False,
        help_text="Enable batch/lot tracking for this item. Automatically sets costing method to Specific Identification."
    )
    
    allow_fractional_quantities = models.BooleanField(
        default=True,
        help_text="Allow decimal quantities (uncheck for whole numbers only like cars, uniforms, etc.)"
    )
    
    track_expiry = models.BooleanField(
        default=False,
        help_text="Track expiry dates for this item (useful for perishable goods)"
    )
    
    # Account Links
    income_account = models.ForeignKey(
        'accounts.Account', 
        on_delete=models.PROTECT,
        related_name='income_items',
        help_text="Account to credit when this item is sold (e.g., 'Sales Revenue').",
        limit_choices_to={'account_type__name': 'Revenue'}
    )
    expense_account = models.ForeignKey(
        'accounts.Account', 
        on_delete=models.PROTECT,
        related_name='expense_items',
        help_text="Account to debit when this item is purchased (e.g., 'Cost of Goods Sold').",
        limit_choices_to={'account_type__name__in': ['Expense', 'Cost of Goods Sold']},
        null=True, blank=True
    )
    asset_account = models.ForeignKey(
        'accounts.Account', 
        on_delete=models.PROTECT,
        related_name='asset_items',
        help_text="The inventory asset account for this item (e.g., 'Inventory Asset').",
        limit_choices_to={'account_type__name': 'Current Asset'},
        null=True, blank=True
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this item is active and available for selection"
    )

    class Meta:
        unique_together = [('company', 'name'), ('company', 'sku')]
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('inventory:item_detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        """Override save to handle batch tracking logic"""
        # If batch tracking is enabled, automatically set costing method to Specific ID
        if self.enable_batch_tracking:
            self.costing_method = self.CostingMethod.SPECIFIC_ID
        
        super().save(*args, **kwargs)
    
    @property
    def current_average_cost(self):
        """Calculate current weighted average cost with price adjustment support"""
        if self.quantity_on_hand <= 0:
            return Decimal('0.00')
        
        if self.costing_method == self.CostingMethod.PRICE_ADJUSTMENT:
            # For price adjustment method, use the latest adjusted cost
            latest_adjustment = self.price_adjustments.first()
            if latest_adjustment:
                return latest_adjustment.new_unit_cost
            # Fall back to weighted average if no adjustments exist
            return self._calculate_weighted_average_cost()
        
        elif self.enable_batch_tracking:
            # For batch tracking, use batch-specific costs
            total_cost = sum(
                batch.quantity_remaining * batch.unit_cost 
                for batch in self.batches.filter(quantity_remaining__gt=0)
            )
            total_quantity = sum(
                batch.quantity_remaining 
                for batch in self.batches.filter(quantity_remaining__gt=0)
            )
        else:
            # Use cost layers
            return self._calculate_weighted_average_cost()
        
        if total_quantity > 0:
            return total_cost / total_quantity
        return Decimal('0.00')

    def _calculate_weighted_average_cost(self):
        """Helper method to calculate weighted average cost"""
        total_cost = sum(
            layer.quantity_remaining * layer.unit_cost 
            for layer in self.cost_layers.filter(quantity_remaining__gt=0)
        )
        total_quantity = sum(
            layer.quantity_remaining 
            for layer in self.cost_layers.filter(quantity_remaining__gt=0)
        )
        
        if total_quantity > 0:
            return total_cost / total_quantity
        return Decimal('0.00')
    
    @property
    def purchase_price(self):
        """Backward compatibility - returns current average cost"""
        return self.current_average_cost

    @property
    def unit_category(self):
        """Get the category of the unit of measurement"""
        for category, units in self.UNIT_CATEGORIES.items():
            if self.unit_of_measurement in units:
                return category
        return 'OTHER'

    @property
    def is_whole_number_item(self):
        """Check if this item should only allow whole numbers"""
        return not self.allow_fractional_quantities

    @property
    def expiring_batches(self):
        """Get batches that are expiring soon (within 30 days)"""
        if not self.track_expiry or not self.enable_batch_tracking:
            return self.batches.none()
        
        from datetime import timedelta
        warning_date = timezone.now().date() + timedelta(days=30)
        return self.batches.filter(
            expiry_date__lte=warning_date,
            quantity_remaining__gt=0
        ).order_by('expiry_date')
    
    @property
    def is_product(self):
        """Check if the item is any kind of physical product."""
        return self.item_type in [self.STOCK_ITEM, self.FINISHED_GOOD]

    def clean(self):
        """Enhanced validation"""
        if self.is_product and not self.sku:
            raise ValidationError("Products (Stock Items and Finished Goods) must have a unique SKU.")
        if self.is_product and not self.expense_account:
            raise ValidationError("Products must have an associated expense account (e.g., Cost of Goods Sold).")
        if self.is_product and not self.asset_account:
            raise ValidationError("Products must have an associated asset account (e.g., Inventory Asset).")
        
        if self.enable_batch_tracking and self.costing_method != self.CostingMethod.SPECIFIC_ID:
            raise ValidationError("Batch tracking requires 'Specific Identification' costing method.")

    @property
    def is_low_on_stock(self):
        if self.is_product and self.reorder_level > 0:
            return self.quantity_on_hand <= self.reorder_level
        return False


class InventoryBatch(models.Model):
    """
    NEW: Batch/Lot tracking for inventory items.
    Used when enable_batch_tracking=True on InventoryItem.
    """
    item = models.ForeignKey(
        InventoryItem, 
        on_delete=models.CASCADE, 
        related_name='batches'
    )
    batch_number = models.CharField(
        max_length=50,
        help_text="Unique batch/lot number"
    )
    manufacture_date = models.DateField(
        null=True, blank=True,
        help_text="Date when this batch was manufactured"
    )
    expiry_date = models.DateField(
        null=True, blank=True,
        help_text="Expiry date for this batch (if applicable)"
    )
    supplier = models.CharField(
        max_length=100, blank=True,
        help_text="Supplier/manufacturer of this batch"
    )
    quantity_remaining = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Quantity remaining in this batch"
    )
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Cost per unit for this batch"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this batch"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['item', 'batch_number']
        ordering = ['expiry_date', 'manufacture_date', 'batch_number']
        verbose_name = "Inventory Batch"
        verbose_name_plural = "Inventory Batches"
    
    def __str__(self):
        return f"{self.item.name} - Batch {self.batch_number}"
    
    @property
    def is_expired(self):
        """Check if this batch has expired"""
        if not self.expiry_date:
            return False
        return self.expiry_date < timezone.now().date()
    
    @property
    def days_to_expiry(self):
        """Get days until expiry (negative if expired)"""
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days
    
    @property
    def is_expiring_soon(self):
        """Check if batch is expiring within 30 days"""
        days = self.days_to_expiry
        return days is not None and 0 <= days <= 30


class InventoryCostLayer(models.Model):
    """
    Tracks different cost layers for inventory items.
    Each purchase creates a new cost layer.
    Used for FIFO, LIFO, and Weighted Average costing methods.
    """
    item = models.ForeignKey(
        InventoryItem, 
        on_delete=models.CASCADE, 
        related_name='cost_layers'
    )
    purchase_date = models.DateTimeField()
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Original quantity purchased at this cost"
    )
    quantity_remaining = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Quantity remaining at this cost layer"
    )
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Cost per unit for this layer"
    )
    reference = models.CharField(
        max_length=100, blank=True,
        help_text="Purchase order or transaction reference"
    )
    
    class Meta:
        ordering = ['purchase_date', 'id']  # FIFO ordering
    
    def __str__(self):
        return f"{self.item.name} - {self.quantity_remaining} @ {self.unit_cost}"

class InventoryPriceAdjustment(models.Model):
    """
    Track price adjustments for inventory items using Price Adjustment costing method.
    This method allows manual adjustment of inventory values for accounting purposes.
    """
    item = models.ForeignKey(
        InventoryItem, 
        on_delete=models.CASCADE, 
        related_name='price_adjustments'
    )
    adjustment_date = models.DateTimeField(default=timezone.now)
    old_unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Previous unit cost before adjustment"
    )
    new_unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="New unit cost after adjustment"
    )
    quantity_affected = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Quantity of inventory affected by this adjustment"
    )
    adjustment_reason = models.CharField(
        max_length=200,
        help_text="Reason for the price adjustment"
    )
    reference = models.CharField(
        max_length=100, blank=True,
        help_text="Reference document or approval number"
    )
    created_by = models.ForeignKey(
        'authentication.User', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='price_adjustments_created'
    )
    
    class Meta:
        ordering = ['-adjustment_date']
        verbose_name = "Price Adjustment"
        verbose_name_plural = "Price Adjustments"
    
    def __str__(self):
        return f"{self.item.name} - Price Adjustment ({self.adjustment_date.date()})"
    
    @property
    def adjustment_amount(self):
        """Calculate total adjustment amount"""
        return (self.new_unit_cost - self.old_unit_cost) * self.quantity_affected
    
    @property
    def adjustment_percentage(self):
        """Calculate adjustment percentage"""
        if self.old_unit_cost > 0:
            return ((self.new_unit_cost - self.old_unit_cost) / self.old_unit_cost) * 100
        return 0
    
class InventoryTransaction(models.Model):
    OPENING_STOCK = 'opening_stock'
    PURCHASE = 'purchase'
    SALES_RETURN = 'sales_return'
    ADJUSTMENT_IN = 'adjustment_in' 
    SALE = 'sale'
    PURCHASE_RETURN = 'purchase_return'
    DAMAGED_GOODS = 'damaged_goods'
    GIFT_OR_PROMOTION = 'gift_or_promotion'
    ADJUSTMENT_OUT = 'adjustment_out' 
    EXPIRED = 'expired_product'
    
    TRANSACTION_TYPE_CHOICES = [
        ('Stock Increases', (
            (OPENING_STOCK, 'Opening Stock'),
            (PURCHASE, 'Purchase from Vendor'),
            (SALES_RETURN, 'Sales Return from Customer'),
            (ADJUSTMENT_IN, 'Positive Adjustment'),
        )),
        ('Stock Decreases', (
            (SALE, 'Sale to Customer'),
            (PURCHASE_RETURN, 'Purchase Return to Vendor'),
            (DAMAGED_GOODS, 'Damaged or Expired Goods'),
            (GIFT_OR_PROMOTION, 'Gift or Promotional Giveaway'),
            (ADJUSTMENT_OUT, 'Negative Adjustment'),
            (EXPIRED, 'Expired Product'),
        )),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='inventory_transactions')
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name='transactions')
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPE_CHOICES)
    
    # NEW: Batch tracking support
    batch = models.ForeignKey(
        InventoryBatch, 
        on_delete=models.PROTECT, 
        null=True, blank=True,
        help_text="Specific batch for this transaction (if batch tracking enabled)"
    )
    
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="The absolute quantity for this transaction (e.g., 10). Must be a positive number."
    )
    
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2, 
        null=True, blank=True,
        help_text="Cost per unit for this transaction"
    )
    total_cost = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text="Total cost for this transaction"
    )
    cost_layers_used = models.JSONField(
        default=list, blank=True,
        help_text="Cost layers consumed for sales transactions"
    )
    
    transaction_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, help_text="Reason for adjustment, related document number, etc.")
    
    class Meta:
        ordering = ['-transaction_date', '-id']
        
    def __str__(self):
        batch_info = f" (Batch: {self.batch.batch_number})" if self.batch else ""
        return f"{self.get_transaction_type_display()} of {self.quantity} for {self.item.name}{batch_info}"
        
    def clean(self):
        """Enhanced validation"""
        if self.quantity <= 0:
            raise ValidationError("Quantity must be a positive number. The transaction type determines the stock movement.")
        
        # Validate batch tracking
        if self.item.enable_batch_tracking and self.transaction_type in self.get_stock_decrease_types():
            if not self.batch:
                raise ValidationError("Batch must be specified for items with batch tracking enabled.")
        
        # Validate fractional quantities
        if not self.item.allow_fractional_quantities and self.quantity % 1 != 0:
            raise ValidationError(f"Item '{self.item.name}' only allows whole number quantities.")
            
    @staticmethod
    def get_stock_decrease_types():
        return [
            InventoryTransaction.SALE, InventoryTransaction.PURCHASE_RETURN,
            InventoryTransaction.DAMAGED_GOODS, InventoryTransaction.GIFT_OR_PROMOTION,
            InventoryTransaction.ADJUSTMENT_OUT, InventoryTransaction.EXPIRED
        ]
        
    def get_quantity_change(self):
        if self.transaction_type in self.get_stock_decrease_types():
            return -self.quantity
        return self.quantity
    
    def save(self, *args, **kwargs):
        """Override save to handle cost layer logic"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.update_cost_layers()
    
    def update_cost_layers(self):
        """Enhanced cost layer update with batch support"""
        if self.transaction_type in [self.PURCHASE, self.OPENING_STOCK, self.SALES_RETURN]:
            if self.item.enable_batch_tracking:
                # Create or update batch
                if not self.batch:
                    # Create new batch if not specified
                    batch_number = f"AUTO-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                    self.batch = InventoryBatch.objects.create(
                        item=self.item,
                        batch_number=batch_number,
                        quantity_remaining=self.quantity,
                        unit_cost=self.unit_cost or self.item.current_average_cost
                    )
                    self.save(update_fields=['batch'])
                else:
                    # Update existing batch
                    self.batch.quantity_remaining += self.quantity
                    self.batch.save()
            else:
                # Create cost layer for non-batch items
                InventoryCostLayer.objects.create(
                    item=self.item,
                    purchase_date=self.transaction_date,
                    quantity=self.quantity,
                    quantity_remaining=self.quantity,
                    unit_cost=self.unit_cost or self.item.current_average_cost,
                    reference=f"{self.transaction_type}-{self.id}"
                )
        
        elif self.transaction_type in [self.SALE, self.PURCHASE_RETURN, self.DAMAGED_GOODS]:
            if self.item.enable_batch_tracking:
                # Consume from specific batch
                if self.batch:
                    self.batch.quantity_remaining -= self.quantity
                    self.batch.save()
                    self.unit_cost = self.batch.unit_cost
                    self.total_cost = self.quantity * self.batch.unit_cost
                    self.save(update_fields=['unit_cost', 'total_cost'])
            else:
                # Consume from cost layers based on costing method
                self.consume_cost_layers()
    
    def consume_cost_layers(self):
        """Enhanced consume cost layers with price adjustment support"""
        remaining_to_consume = self.quantity
        layers_used = []
        total_cost = Decimal('0.00')
        
        if self.item.costing_method == InventoryItem.CostingMethod.PRICE_ADJUSTMENT:
            # Use current adjusted price for all transactions
            adjusted_cost = self.item.current_average_cost
            total_cost = remaining_to_consume * adjusted_cost
            
            # Reduce all layers proportionally (similar to weighted average)
            total_remaining = sum(
                layer.quantity_remaining 
                for layer in self.item.cost_layers.filter(quantity_remaining__gt=0)
            )
            
            if total_remaining > 0:
                for layer in self.item.cost_layers.filter(quantity_remaining__gt=0):
                    proportion = layer.quantity_remaining / total_remaining
                    quantity_to_reduce = remaining_to_consume * proportion
                    
                    if quantity_to_reduce > 0:
                        layer.quantity_remaining -= quantity_to_reduce
                        layer.save()
                        
                        layers_used.append({
                            'layer_id': layer.id,
                            'quantity': float(quantity_to_reduce),
                            'unit_cost': float(adjusted_cost)  # Use adjusted cost
                        })
            
            self.unit_cost = adjusted_cost
            self.total_cost = total_cost
            self.cost_layers_used = layers_used
            self.save(update_fields=['unit_cost', 'total_cost', 'cost_layers_used'])
            return
        
        elif self.item.costing_method == InventoryItem.CostingMethod.FIFO:
            # First In, First Out
            cost_layers = self.item.cost_layers.filter(
                quantity_remaining__gt=0
            ).order_by('purchase_date', 'id')
        
        elif self.item.costing_method == InventoryItem.CostingMethod.LIFO:
            # Last In, First Out
            cost_layers = self.item.cost_layers.filter(
                quantity_remaining__gt=0
            ).order_by('-purchase_date', '-id')
        
        else:  # Weighted Average
            # Use weighted average cost
            avg_cost = self.item.current_average_cost
            total_cost = remaining_to_consume * avg_cost
            
            # Reduce all layers proportionally
            total_remaining = sum(
                layer.quantity_remaining 
                for layer in self.item.cost_layers.filter(quantity_remaining__gt=0)
            )
            
            if total_remaining > 0:
                for layer in self.item.cost_layers.filter(quantity_remaining__gt=0):
                    proportion = layer.quantity_remaining / total_remaining
                    quantity_to_reduce = remaining_to_consume * proportion
                    
                    if quantity_to_reduce > 0:
                        layer.quantity_remaining -= quantity_to_reduce
                        layer.save()
                        
                        layers_used.append({
                            'layer_id': layer.id,
                            'quantity': float(quantity_to_reduce),
                            'unit_cost': float(layer.unit_cost)
                        })
            
            self.unit_cost = avg_cost
            self.total_cost = total_cost
            self.cost_layers_used = layers_used
            self.save(update_fields=['unit_cost', 'total_cost', 'cost_layers_used'])
            return
        
        # For FIFO and LIFO (existing logic continues...)
        for layer in cost_layers:
            if remaining_to_consume <= 0:
                break
            
            quantity_from_layer = min(remaining_to_consume, layer.quantity_remaining)
            
            layer.quantity_remaining -= quantity_from_layer
            layer.save()
            
            cost_from_layer = quantity_from_layer * layer.unit_cost
            total_cost += cost_from_layer
            
            layers_used.append({
                'layer_id': layer.id,
                'quantity': float(quantity_from_layer),
                'unit_cost': float(layer.unit_cost)
            })
            
            remaining_to_consume -= quantity_from_layer
        
        # Calculate weighted average cost for this transaction
        if self.quantity > 0:
            self.unit_cost = total_cost / self.quantity
        else:
            self.unit_cost = Decimal('0.00')
        
        self.total_cost = total_cost
        self.cost_layers_used = layers_used
        self.save(update_fields=['unit_cost', 'total_cost', 'cost_layers_used'])


# NEW: Inventory Movement Model for stock adjustments
class InventoryMovement(models.Model):
    """
    Separate model for inventory movements/adjustments by stock keepers.
    This provides better audit trail and control.
    """
    MOVEMENT_REASONS = [
        ('DAMAGED', 'Item Damaged'),
        ('EXPIRED', 'Item Expired'),
        ('GIFT', 'Gift/Promotional'),
        ('CORRECTION', 'Quantity Correction'),
        ('THEFT', 'Theft/Loss'),
        ('RETURN', 'Customer Return'),
        ('TRANSFER', 'Transfer Between Locations'),
        ('CUSTOM', 'Other (Custom Reason)'),
    ]
    
    MOVEMENT_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]
    
    # 🆕 REASONS THAT REQUIRE FAIR MARKET VALUE
    FAIR_VALUE_REQUIRED_REASONS = ['GIFT', 'RETURN', 'CORRECTION']
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='inventory_movements')
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='movements')
    batch = models.ForeignKey(
        InventoryBatch, 
        on_delete=models.PROTECT, 
        null=True, blank=True,
        help_text="Specific batch for this movement (if batch tracking enabled)"
    )
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES)
    reason = models.CharField(max_length=20, choices=MOVEMENT_REASONS)
    custom_reason = models.CharField(
        max_length=100, blank=True,
        help_text="Custom reason if 'Other' is selected"
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Quantity to move (always positive)"
    )
    
    # 🆕 ADD FAIR MARKET VALUE FIELD
    fair_market_value = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Fair market value per unit for gifts/donations or custom valuations"
    )
    
    reference_document = models.CharField(
        max_length=100, blank=True,
        help_text="Reference document number"
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'authentication.User', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='inventory_movements_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Audit fields - prevent editing/deletion
    is_processed = models.BooleanField(default=False, editable=False)
    processed_at = models.DateTimeField(null=True, blank=True, editable=False)
    
    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("can_create_movement", "Can create inventory movements"),
        ]
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.item.name} ({self.quantity})"
    
    def clean(self):
        """Enhanced validation with fair market value"""
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        
        if not self.item.allow_fractional_quantities and self.quantity % 1 != 0:
            raise ValidationError(f"Item '{self.item.name}' only allows whole number quantities.")
        
        if self.reason == 'CUSTOM' and not self.custom_reason:
            raise ValidationError("Custom reason is required when 'Other' is selected.")
        
        # 🆕 REQUIRE FAIR MARKET VALUE FOR SPECIFIC SCENARIOS
        if self.movement_type == 'IN' and self.reason in self.FAIR_VALUE_REQUIRED_REASONS:
            if not self.fair_market_value or self.fair_market_value <= 0:
                reason_display = dict(self.MOVEMENT_REASONS)[self.reason]
                raise ValidationError(
                    f"Fair market value is required for '{reason_display}' stock-in movements "
                    f"to maintain accurate inventory valuation."
                )
        
        if self.item.enable_batch_tracking and not self.batch:
            raise ValidationError("Batch must be specified for items with batch tracking enabled.")
    
    def process_movement(self):
        """Enhanced process movement with fair market value support"""
        if self.is_processed:
            raise ValidationError("Movement has already been processed.")
        
        # Determine transaction type and unit cost
        transaction_type = InventoryTransaction.ADJUSTMENT_IN if self.movement_type == 'IN' else InventoryTransaction.ADJUSTMENT_OUT
        
        # 🆕 SMART UNIT COST CALCULATION
        unit_cost = None
        if self.movement_type == 'IN':
            if self.reason in self.FAIR_VALUE_REQUIRED_REASONS and self.fair_market_value:
                # Use fair market value for gifts, returns, corrections
                unit_cost = self.fair_market_value
            elif self.reason not in self.FAIR_VALUE_REQUIRED_REASONS:
                # Use current average cost for other stock-in movements
                unit_cost = self.item.current_average_cost or Decimal('0.00')
        else:
            # For stock-out movements, use current average cost
            unit_cost = self.item.current_average_cost or Decimal('0.00')
        
        # Create corresponding inventory transaction
        transaction = InventoryTransaction.objects.create(
            company=self.company,
            item=self.item,
            batch=self.batch,
            transaction_type=transaction_type,
            quantity=self.quantity,
            unit_cost=unit_cost,  # 🆕 USE CALCULATED UNIT COST
            transaction_date=self.created_at,
            notes=f"Movement: {self.get_reason_display()} - {self.notes}"
        )
        
        # Update item quantity
        quantity_change = self.quantity if self.movement_type == 'IN' else -self.quantity
        self.item.quantity_on_hand += quantity_change
        self.item.save(update_fields=['quantity_on_hand'])
        
        # Mark as processed
        self.is_processed = True
        self.processed_at = timezone.now()
        self.save(update_fields=['is_processed', 'processed_at'])
        
        # 🆕 CREATE JOURNAL ENTRY FOR SPECIAL MOVEMENTS
        if self.movement_type == 'IN' and self.reason in self.FAIR_VALUE_REQUIRED_REASONS and self.fair_market_value:
            self.create_special_movement_journal_entry(transaction)
    
    def create_special_movement_journal_entry(self, transaction):
        """Create journal entry for special inventory movements (gifts, returns, corrections)"""
        from apps.journal.models import JournalEntry, JournalEntryLine
        from apps.accounts.models import Account
        
        total_value = self.quantity * self.fair_market_value
        
        # --- DEFINITIVE FIX ---
        # The JournalEntry model has 'date', not 'transaction_date', and no 'reference' or 'total_amount' field.
        description_text = f"{self.get_reason_display()}: {self.item.name} (Ref: {self.reason}-{self.id})"

        journal_entry = JournalEntry.objects.create(
            company=self.company,
            date=self.created_at.date(),
            description=description_text,
            created_by=self.created_by
        )
        
        # Debit Inventory Asset (always)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.item.asset_account,
            description=f"{self.get_reason_display()} - {self.item.name} ({self.quantity} units)",
            debit_amount=total_value,
            credit_amount=0
        )
        
        # CREDIT APPROPRIATE ACCOUNT BASED ON REASON
        credit_account = self._get_credit_account_for_reason()
        
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=credit_account,
            description=f"{self.get_reason_display()} - {self.item.name}",
            debit_amount=0,
            credit_amount=total_value
        )
    
    def _get_credit_account_for_reason(self):
        """Get appropriate credit account based on movement reason"""
        from apps.accounts.models import Account, AccountType
        
        account_configs = {
            'GIFT': {
                'name': 'Donation Income',
                'account_number': '4900',
                'description': 'Income from donated items',
                'account_type': 'Revenue'
            },
            'RETURN': {
                'name': 'Customer Returns',
                'account_number': '4910',
                'description': 'Value of returned merchandise',
                'account_type': 'Revenue'
            },
            'CORRECTION': {
                'name': 'Inventory Adjustments',
                'account_number': '4920',
                'description': 'Inventory quantity/value corrections',
                'account_type': 'Revenue'
            }
        }
        
        config = account_configs.get(self.reason, account_configs['GIFT'])
        
        try:
            # Try to find existing account
            account = Account.objects.get(
                company=self.company,
                name__icontains=config['name'].split()[0]
            )
        except Account.DoesNotExist:
            # --- DEFINITIVE FIX ---
            # AccountType is global, so we don't filter by company.
            account_type = AccountType.objects.get(name=config['account_type'])
            account = Account.objects.create(
                company=self.company,
                account_type=account_type,
                name=config['name'],
                account_number=config['account_number'],
                description=config['description']
            )
        
        return account