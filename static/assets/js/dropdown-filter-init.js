// C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\static\assets\js\dropdown-filter-init.js
/**
 * Dropdown Filter Initialization
 * This script automatically initializes dropdown filters across the application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dropdown filters with data-filter attribute
    initializeAllDropdownFilters();
    
    // Initialize smart search fields
    initializeAllSmartSearchFields();
});

function initializeAllDropdownFilters() {
    // For regular select elements that need filtering
    const filterSelects = document.querySelectorAll('select[data-filter="true"]');
    
    filterSelects.forEach(select => {
        if (window.jQuery && window.jQuery.fn.dropdownFilter) {
            jQuery(select).dropdownFilter({
                filterPlaceholder: select.dataset.placeholder || 'Search...',
                noResultsText: 'No matching items found',
                maxHeight: '250px'
            });
        } else {
            console.warn('jQuery or dropdownFilter plugin not loaded');
        }
    });
    
    // For dropdown containers with data-filter attribute
    if (window.jQuery) {
        jQuery('.dropdown[data-filter="true"]').dropdownFilter({
            filterPlaceholder: 'Search...',
            noResultsText: 'No matching items found',
            maxHeight: '250px'
        });
    }
}

function initializeAllSmartSearchFields() {
    // For API-based smart search fields
    const smartSearchInputs = document.querySelectorAll('.smart-search-input');
    
    smartSearchInputs.forEach(input => {
        if (window.SmartSearch && input.dataset.url) {
            new SmartSearch(input, input.dataset.url, {
                placeholder: input.dataset.placeholder || 'Search...',
                allowCreate: input.dataset.allowCreate === 'true',
                createUrl: input.dataset.createUrl || null
            });
        }
    });
}
