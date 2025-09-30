// C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\static\assets\js\transaction-form.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize form functionality
    initializeTransactionForm();
});

function initializeTransactionForm() {
    // Handle transaction type changes
    const transactionTypeSelect = document.getElementById('id_transaction_type');
    if (transactionTypeSelect) {
        transactionTypeSelect.addEventListener('change', handleTransactionTypeChange);
        // Trigger initial load
        handleTransactionTypeChange();
    }

    // Handle line items toggle
    const useLineItemsCheckbox = document.getElementById('id_use_line_items');
    if (useLineItemsCheckbox) {
        useLineItemsCheckbox.addEventListener('change', toggleLineItems);
        // Trigger initial state
        toggleLineItems();
    }

    // Initialize customer search
    initializeCustomerSearch();
    
    // Initialize item selects in formset
    initializeItemSelects();
    
    // Handle formset add/remove
    setupFormsetHandlers();
}

function handleTransactionTypeChange() {
    const transactionType = document.getElementById('id_transaction_type').value;
    
    if (transactionType) {
        // Update categories based on transaction type
        updateCategories(transactionType);
    }
}

function updateCategories(transactionType) {
    const categorySelect = document.getElementById('id_category');
    if (!categorySelect) return;

    // Store current selection
    const currentValue = categorySelect.value;
    
    // Show loading state
    categorySelect.innerHTML = '<option value="">Loading categories...</option>';
    categorySelect.disabled = true;

    // Filter categories (this would normally be an AJAX call, but we'll do it client-side for now)
    // Reset to all options and let the backend handle filtering
    setTimeout(() => {
        categorySelect.disabled = false;
        // The backend form should handle the filtering
        if (currentValue) {
            categorySelect.value = currentValue;
        }
    }, 100);
}

function toggleLineItems() {
    const useLineItems = document.getElementById('id_use_line_items').checked;
    const lineItemsSection = document.querySelector('.line-items-section');
    const manualTotalSection = document.querySelector('.manual-total-section');
    
    if (lineItemsSection) {
        lineItemsSection.style.display = useLineItems ? 'block' : 'none';
    }
    
    if (manualTotalSection) {
        manualTotalSection.style.display = useLineItems ? 'none' : 'block';
    }
    
    // Update required fields
    const manualTotalInput = document.getElementById('id_manual_total_amount');
    if (manualTotalInput) {
        manualTotalInput.required = !useLineItems;
    }
}

function initializeCustomerSearch() {
    const customerSelect = document.getElementById('id_customer');
    if (!customerSelect) return;

    // Add search functionality (basic implementation)
    // You can enhance this with a proper search widget later
}

function initializeItemSelects() {
    // Handle item selection changes in formset
    document.querySelectorAll('.item-select').forEach(select => {
        select.addEventListener('change', function() {
            updateItemDetails(this);
        });
    });
}

function updateItemDetails(itemSelect) {
    const row = itemSelect.closest('.formset-row');
    if (!row) return;

    const selectedOption = itemSelect.options[itemSelect.selectedIndex];
    if (!selectedOption.value) return;

    // Update unit price from data attributes
    const unitPriceInput = row.querySelector('.unit-price');
    const descriptionInput = row.querySelector('.line-description');
    
    if (unitPriceInput && selectedOption.dataset.salePrice) {
        unitPriceInput.value = selectedOption.dataset.salePrice;
    }
    
    if (descriptionInput && selectedOption.dataset.description) {
        descriptionInput.value = selectedOption.dataset.description;
    }
    
    // Trigger total calculation
    calculateRowTotal(row);
}

function calculateRowTotal(row) {
    const quantityInput = row.querySelector('.quantity');
    const unitPriceInput = row.querySelector('.unit-price');
    const totalSpan = row.querySelector('.line-total');
    
    if (quantityInput && unitPriceInput && totalSpan) {
        const quantity = parseFloat(quantityInput.value) || 0;
        const unitPrice = parseFloat(unitPriceInput.value) || 0;
        const total = quantity * unitPrice;
        
        totalSpan.textContent = total.toFixed(2);
        
        // Update grand total
        updateGrandTotal();
    }
}

function updateGrandTotal() {
    let grandTotal = 0;
    document.querySelectorAll('.line-total').forEach(totalSpan => {
        grandTotal += parseFloat(totalSpan.textContent) || 0;
    });
    
    const grandTotalSpan = document.getElementById('grand-total');
    if (grandTotalSpan) {
        grandTotalSpan.textContent = grandTotal.toFixed(2);
    }
}

function setupFormsetHandlers() {
    // Handle quantity and price changes
    document.addEventListener('input', function(e) {
        if (e.target.matches('.quantity, .unit-price')) {
            const row = e.target.closest('.formset-row');
            if (row) {
                calculateRowTotal(row);
            }
        }
    });
    
    // Handle add row button
    document.addEventListener('click', function(e) {
        if (e.target.matches('.add-row-btn')) {
            e.preventDefault();
            addFormsetRow();
        }
        
        if (e.target.matches('.remove-row-btn')) {
            e.preventDefault();
            removeFormsetRow(e.target);
        }
    });
}

function addFormsetRow() {
    // This is a simplified version - you might need to adjust based on your formset implementation
    const formsetContainer = document.querySelector('.formset-container');
    if (!formsetContainer) return;
    
    const totalFormsInput = document.querySelector('[name$="-TOTAL_FORMS"]');
    if (!totalFormsInput) return;
    
    const currentFormCount = parseInt(totalFormsInput.value);
    const newFormCount = currentFormCount + 1;
    
    // Clone the last form and update its indices
    const lastForm = formsetContainer.querySelector('.formset-row:last-child');
    if (lastForm) {
        const newForm = lastForm.cloneNode(true);
        
        // Update form indices
        newForm.innerHTML = newForm.innerHTML.replace(
            new RegExp(`-${currentFormCount - 1}-`, 'g'),
            `-${currentFormCount}-`
        );
        
        // Clear values
        newForm.querySelectorAll('input, select, textarea').forEach(input => {
            if (input.type !== 'hidden') {
                input.value = '';
            }
        });
        
        // Add to container
        formsetContainer.appendChild(newForm);
        
        // Update total forms count
        totalFormsInput.value = newFormCount;
        
        // Initialize new row
        initializeItemSelects();
    }
}

function removeFormsetRow(button) {
    const row = button.closest('.formset-row');
    if (!row) return;
    
    const deleteCheckbox = row.querySelector('[name$="-DELETE"]');
    if (deleteCheckbox) {
        deleteCheckbox.checked = true;
        row.style.display = 'none';
    } else {
        row.remove();
    }
    
    updateGrandTotal();
}

// Utility function for CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
