// C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\static\assets\js\smart-inventory.js
class SmartInventoryManager {
    constructor() {
        console.log('🚀 SmartInventoryManager initializing...');
        this.initializeFormHandlers();
        this.setupFormsetManagement();
        this.initializeExistingRows();
        console.log('✅ SmartInventoryManager initialized');
    }

    initializeFormHandlers() {
        // Handle item selection changes
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('inventory-item-select')) {
                console.log('📦 Item selection changed:', e.target.value);
                this.handleItemSelection(e.target);
            }
        });

        // Handle quantity and price changes for real-time calculation
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('quantity-input') || 
                e.target.classList.contains('unit-price-input')) {
                console.log('💰 Price/Quantity changed');
                this.updateRowTotal(e.target.closest('.line-item-row'));
                this.updateGrandTotal();
            }
        });

        // Handle add/remove row buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-row-btn')) {
                e.preventDefault();
                console.log('➕ Adding new row');
                this.addFormsetRow();
            }
            if (e.target.classList.contains('remove-row-btn')) {
                e.preventDefault();
                console.log('❌ Removing row');
                this.removeFormsetRow(e.target.closest('.formset-row'));
            }
        });
    }

    async handleItemSelection(itemSelect) {
        const row = itemSelect.closest('.line-item-row');
        const itemId = itemSelect.value;

        if (!itemId) {
            this.clearRowData(row);
            return;
        }

        try {
            console.log('🔍 Loading item details for ID:', itemId);
            const response = await fetch(`/inventory/ajax/item/${itemId}/`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📊 Item data received:', data);

            if (data.error) {
                console.error('❌ API Error:', data.error);
                return;
            }

            // Populate row with item data
            this.populateRowData(row, data);
            
        } catch (error) {
            console.error('❌ Error loading item details:', error);
            // Fallback: try to get data from select option attributes
            this.populateFromSelectOption(itemSelect, row);
        }
    }

    populateFromSelectOption(itemSelect, row) {
        const selectedOption = itemSelect.options[itemSelect.selectedIndex];
        if (!selectedOption || !selectedOption.value) return;

        console.log('🔄 Using fallback data from select option');
        
        // Get data from option attributes
        const data = {
            description: selectedOption.dataset.description || '',
            sale_price: selectedOption.dataset.salePrice || '0.00',
            purchase_price: selectedOption.dataset.purchasePrice || '0.00',
            unit_of_measurement: selectedOption.dataset.unit || 'units',
            quantity_on_hand: selectedOption.dataset.quantity || '0'
        };

        this.populateRowData(row, data);
    }

    populateRowData(row, data) {
        console.log('📝 Populating row with data:', data);

        // Set description
        const descInput = row.querySelector('.description-input');
        if (descInput && data.description) {
            descInput.value = data.description;
        }

        // Set unit display
        const unitDisplay = row.querySelector('.unit-display');
        if (unitDisplay) {
            unitDisplay.textContent = data.unit_of_measurement || 'units';
        }

        // Set available quantity
        const availableQty = row.querySelector('.available-qty');
        if (availableQty) {
            availableQty.textContent = data.quantity_on_hand || '0';
        }

        // Set price based on transaction type
        const unitPriceInput = row.querySelector('.unit-price-input');
        const transactionType = document.getElementById('id_transaction_type')?.value;
        
        if (unitPriceInput) {
            let price = '0.00';
            if (transactionType === 'SALE') {
                price = data.sale_price || '0.00';
            } else if (transactionType === 'PURCHASE') {
                price = data.purchase_price || '0.00';
            } else {
                price = data.sale_price || '0.00';
            }
            unitPriceInput.value = price;
            console.log('💰 Set price to:', price);
        }

        // Handle batch tracking
        if (data.enable_batch_tracking) {
            this.loadBatches(data.id, row);
        }

        // Set quantity step based on fractional allowance
        const quantityInput = row.querySelector('.quantity-input');
        if (quantityInput) {
            quantityInput.step = data.allow_fractional_quantities ? '0.01' : '1';
        }

        // Update totals
        this.updateRowTotal(row);
        this.updateGrandTotal();
    }

    clearRowData(row) {
        console.log('🧹 Clearing row data');
        const inputs = row.querySelectorAll('input:not([name*="DELETE"]):not([name*="id"]), select:not([name*="DELETE"])');
        inputs.forEach(input => {
            if (input.type !== 'hidden') {
                input.value = '';
            }
        });

        const displays = row.querySelectorAll('.unit-display, .available-qty, .line-total-display');
        displays.forEach(display => display.textContent = '');

        this.updateGrandTotal();
    }

    async loadBatches(itemId, row) {
        const batchSelect = row.querySelector('.batch-select');
        if (!batchSelect) return;

        try {
            const response = await fetch(`/inventory/ajax/batches/${itemId}/`);
            const data = await response.json();

            batchSelect.innerHTML = '<option value="">Select Batch</option>';
            batchSelect.style.display = 'block';

            if (data.batches && data.batches.length > 0) {
                data.batches.forEach(batch => {
                    const option = document.createElement('option');
                    option.value = batch.id;
                    option.textContent = `${batch.batch_number} (Qty: ${batch.quantity_remaining})`;
                    batchSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('❌ Error loading batches:', error);
        }
    }

    updateRowTotal(row) {
        const quantityInput = row.querySelector('.quantity-input');
        const unitPriceInput = row.querySelector('.unit-price-input');
        const totalDisplay = row.querySelector('.line-total-display');

        if (quantityInput && unitPriceInput && totalDisplay) {
            const quantity = parseFloat(quantityInput.value) || 0;
            const unitPrice = parseFloat(unitPriceInput.value) || 0;
            const total = quantity * unitPrice;
            
            totalDisplay.textContent = total.toFixed(2);
            console.log('📊 Row total updated:', total.toFixed(2));
        }
    }

    updateGrandTotal() {
        let grandTotal = 0;
        const lineTotals = document.querySelectorAll('.line-total-display');
        
        lineTotals.forEach(totalDisplay => {
            const amount = parseFloat(totalDisplay.textContent) || 0;
            grandTotal += amount;
        });

        console.log('💰 Grand total calculated:', grandTotal.toFixed(2));

        // Update all total displays
        const transactionTotalInput = document.getElementById('transaction-total');
        if (transactionTotalInput) {
            transactionTotalInput.value = grandTotal.toFixed(2);
        }

        // Update manual total if line items are not being used
        const manualTotalInput = document.getElementById('id_manual_total_amount');
        const useLineItems = document.getElementById('id_use_line_items');
        
        if (useLineItems && useLineItems.checked && manualTotalInput) {
            manualTotalInput.value = grandTotal.toFixed(2);
        }

        // Update amount paid if "paid in full" is checked
        this.updateAmountPaid();
    }

    updateAmountPaid() {
        const paidInFullCheckbox = document.getElementById('id_paid_in_full');
        const amountPaidInput = document.getElementById('id_amount_paid');
        const transactionTotalInput = document.getElementById('transaction-total');

        if (paidInFullCheckbox && paidInFullCheckbox.checked && 
            amountPaidInput && transactionTotalInput) {
            amountPaidInput.value = transactionTotalInput.value;
        }
    }

    setupFormsetManagement() {
        this.updateFormsetManagement();
    }

    addFormsetRow() {
        const tbody = document.querySelector('.formset-container');
        const totalFormsInput = document.querySelector('[name$="-TOTAL_FORMS"]');
        
        if (!tbody || !totalFormsInput) {
            console.error('❌ Cannot find formset container or total forms input');
            return;
        }

        const formCount = parseInt(totalFormsInput.value);
        const template = document.querySelector('.formset-row');
        
        if (!template) {
            console.error('❌ Cannot find template row');
            return;
        }

        const newRow = template.cloneNode(true);
        
        // Update form field names and IDs
        const inputs = newRow.querySelectorAll('input, select');
        inputs.forEach(input => {
            if (input.name) {
                input.name = input.name.replace(/-\d+-/, `-${formCount}-`);
                if (input.id) {
                    input.id = input.id.replace(/_\d+_/, `_${formCount}_`);
                }
                // Clear values except for hidden fields
                if (input.type !== 'hidden' || input.name.includes('DELETE')) {
                    input.value = '';
                }
            }
        });

        // Clear displays
        const displays = newRow.querySelectorAll('.unit-display, .available-qty, .line-total-display');
        displays.forEach(display => display.textContent = '');

        // Hide batch select
        const batchSelect = newRow.querySelector('.batch-select');
        if (batchSelect) {
            batchSelect.style.display = 'none';
        }

        tbody.appendChild(newRow);
        totalFormsInput.value = formCount + 1;
        
        this.updateFormsetManagement();
        console.log('✅ New row added, total forms:', formCount + 1);
    }

    removeFormsetRow(row) {
        const deleteInput = row.querySelector('[name$="-DELETE"]');
        if (deleteInput) {
            deleteInput.checked = true;
            row.style.display = 'none';
            console.log('🗑️ Row marked for deletion');
        } else {
            row.remove();
            console.log('🗑️ Row removed from DOM');
        }
        
        this.updateGrandTotal();
        this.updateFormsetManagement();
    }

    updateFormsetManagement() {
        const rows = document.querySelectorAll('.formset-row:not([style*="display: none"])');
        
        rows.forEach((row, index) => {
            const actionCell = row.querySelector('td:last-child');
            if (!actionCell) return;

            if (index === 0) {
                // First row should have add button
                actionCell.innerHTML = '<button type="button" class="btn btn-add add-row-btn" title="Add Row">+</button>';
            } else {
                // Other rows should have remove button
                actionCell.innerHTML = '<button type="button" class="btn btn-remove remove-row-btn" title="Remove Row">×</button>';
            }
        });
    }

    initializeExistingRows() {
        // Initialize any existing rows on page load
        const existingRows = document.querySelectorAll('.line-item-row');
        existingRows.forEach(row => {
            const itemSelect = row.querySelector('.inventory-item-select');
            if (itemSelect && itemSelect.value) {
                console.log('🔄 Initializing existing row with item:', itemSelect.value);
                // Use timeout to ensure DOM is ready
                setTimeout(() => {
                    this.handleItemSelection(itemSelect);
                }, 100);
            }
        });

        // Update totals for any existing data
        setTimeout(() => {
            this.updateGrandTotal();
        }, 200);
    }
}

// Export for global use
window.SmartInventoryManager = SmartInventoryManager;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌟 DOM loaded, initializing SmartInventoryManager');
    window.smartInventoryManager = new SmartInventoryManager();
});
