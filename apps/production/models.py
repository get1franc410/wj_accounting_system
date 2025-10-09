# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\production\models.py

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.core.models import Company
from apps.inventory.models import InventoryItem
from apps.authentication.models import User

class ProductionFormula(models.Model):
    """
    Defines the recipe/formula for producing a finished product,
    including all required materials and their quantities.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='production_formulas')
    name = models.CharField(max_length=255, help_text="Name of the production formula/recipe")
    finished_product = models.ForeignKey(
        InventoryItem, 
        on_delete=models.CASCADE, 
        related_name='production_formulas',
        help_text="The finished product that will be created",
        limit_choices_to={'item_type': InventoryItem.FINISHED_GOOD}
    )
    unit_quantity = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="How many units this formula produces (e.g., 1 cake, 5 gallons)"
    )
    description = models.TextField(blank=True, help_text="Description of the production process")
    labor_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Labor cost per unit produced"
    )
    overhead_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Overhead cost per unit produced (electricity, etc.)"
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_formulas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [('company', 'name')]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.finished_product.name})"
    
    @property
    def material_cost(self):
        """Calculate the total material cost for this formula"""
        return sum(item.total_cost for item in self.ingredients.all())
    
    @property
    def total_cost_per_unit(self):
        """Calculate the total cost per unit including materials, labor and overhead"""
        return self.material_cost + self.labor_cost + self.overhead_cost
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage based on finished product sale price"""
        if self.finished_product.sale_price > 0:
            cost = self.total_cost_per_unit
            if cost > 0:
                return ((self.finished_product.sale_price - cost) / cost) * 100
        return 0


class FormulaIngredient(models.Model):
    """
    Represents a single ingredient in a production formula with its required quantity.
    """
    formula = models.ForeignKey(ProductionFormula, on_delete=models.CASCADE, related_name='ingredients')
    material = models.ForeignKey(
        InventoryItem, 
        on_delete=models.CASCADE, 
        related_name='used_in_formulas',
        help_text="Raw material or component used in production",
        limit_choices_to={'item_type': InventoryItem.STOCK_ITEM}
    )
    quantity = models.DecimalField(
        max_digits=12, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="Quantity of this material needed per formula unit"
    )
    notes = models.CharField(max_length=255, blank=True)
    
    class Meta:
        unique_together = [('formula', 'material')]
        ordering = ['material__name']
    
    def __str__(self):
        return f"{self.material.name} ({self.quantity} {self.material.unit_of_measurement})"
    
    @property
    def total_cost(self):
        """Calculate the total cost for this ingredient based on current average cost"""
        return self.quantity * self.material.current_average_cost


class ProductionOrder(models.Model):
    """
    Represents a production run using a specific formula to create finished products.
    """
    class Status(models.TextChoices):
        PLANNED = 'PLANNED', 'Planned'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='production_orders')
    formula = models.ForeignKey(ProductionFormula, on_delete=models.PROTECT, related_name='production_orders')
    order_number = models.CharField(max_length=50, blank=True)
    quantity = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Number of units to produce"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    planned_date = models.DateField(default=timezone.now)
    start_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    actual_labor_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actual_overhead_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_production_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-planned_date', '-created_at']
    
    def __str__(self):
        return f"PO-{self.id}: {self.formula.name} ({self.quantity} units)"
    
    def save(self, *args, **kwargs):
        # Generate order number if not provided
        if not self.order_number:
            self.order_number = f"PO-{timezone.now().strftime('%Y%m%d')}-{self.id or 'NEW'}"
        super().save(*args, **kwargs)
    
    @property
    def estimated_material_cost(self):
        """Calculate the estimated material cost for this production order"""
        return self.formula.material_cost * self.quantity
    
    @property
    def estimated_labor_cost(self):
        """Calculate the estimated labor cost for this production order"""
        return self.formula.labor_cost * self.quantity
    
    @property
    def estimated_overhead_cost(self):
        """Calculate the estimated overhead cost for this production order"""
        return self.formula.overhead_cost * self.quantity
    
    @property
    def estimated_total_cost(self):
        """Calculate the estimated total cost for this production order"""
        return self.estimated_material_cost + self.estimated_labor_cost + self.estimated_overhead_cost
    
    @property
    def actual_total_cost(self):
        """Calculate the actual total cost if available"""
        material_cost = sum(item.actual_cost for item in self.material_usages.all())
        labor = self.actual_labor_cost or self.estimated_labor_cost
        overhead = self.actual_overhead_cost or self.estimated_overhead_cost
        return material_cost + labor + overhead
    
    @property
    def material_status(self):
        """Check if we have enough materials for this production order"""
        for ingredient in self.formula.ingredients.all():
            required = ingredient.quantity * self.quantity
            if ingredient.material.quantity_on_hand < required:
                return False
        return True


class MaterialUsage(models.Model):
    """
    Records the actual material usage for a production order.
    """
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name='material_usages')
    material = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='production_usages')
    planned_quantity = models.DecimalField(max_digits=12, decimal_places=4)
    actual_quantity = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    batch = models.ForeignKey(
        'inventory.InventoryBatch', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='production_usages'
    )
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    usage_date = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    
    class Meta:
        unique_together = [('production_order', 'material', 'batch')]
    
    def __str__(self):
        return f"{self.material.name} for {self.production_order}"
    
    @property
    def actual_cost(self):
        """Calculate the actual cost of this material usage"""
        if self.actual_quantity and self.unit_cost:
            return self.actual_quantity * self.unit_cost
        return Decimal('0.00')
    
    @property
    def variance(self):
        """Calculate the variance between planned and actual quantity"""
        if self.actual_quantity:
            return self.actual_quantity - self.planned_quantity
        return Decimal('0.00')


class ProductionWaste(models.Model):
    """
    Records waste generated during production.
    """
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name='waste_records')
    material = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='waste_records')
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    reason = models.CharField(max_length=255)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Waste: {self.quantity} {self.material.unit_of_measurement} of {self.material.name}"
