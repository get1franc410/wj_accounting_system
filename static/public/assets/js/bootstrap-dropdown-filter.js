// C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\static\assets\js\bootstrap-dropdown-filter.js
(function($) {
    'use strict';
    
    $.fn.dropdownFilter = function(options) {
        const settings = $.extend({
            filterPlaceholder: 'Search...',
            noResultsText: 'No results found',
            autoFocus: true,
            maxHeight: '200px'
        }, options);
        
        return this.each(function() {
            const $dropdown = $(this);
            
            // 🆕 CHECK IF IT'S A SELECT DROPDOWN OR BOOTSTRAP DROPDOWN
            const $select = $dropdown.find('select');
            const $menu = $dropdown.find('.dropdown-menu');
            
            if ($select.length > 0) {
                // 🆕 HANDLE SELECT DROPDOWNS (for forms)
                initSelectDropdown($dropdown, $select, settings);
            } else if ($menu.length > 0) {
                // 🆕 HANDLE BOOTSTRAP DROPDOWNS (existing functionality)
                initBootstrapDropdown($dropdown, $menu, settings);
            }
        });
    };
    
    // 🆕 FUNCTION FOR SELECT DROPDOWNS
    function initSelectDropdown($dropdown, $select, settings) {
        // Create filter input
        const $filterContainer = $('<div class="dropdown-filter-container p-2 border-bottom"></div>');
        const $filterInput = $('<input type="text" class="form-control form-control-sm" placeholder="' + settings.filterPlaceholder + '">');
        
        $filterContainer.append($filterInput);
        
        // Insert filter above the select
        $select.before($filterContainer);
        
        // Make select scrollable
        $select.css({
            'max-height': settings.maxHeight,
            'overflow-y': 'auto'
        });
        
        // Store original options
        const originalOptions = $select.find('option').clone();
        
        // Filter functionality
        $filterInput.on('input', function() {
            const filterValue = $(this).val().toLowerCase();
            let hasVisibleOptions = false;
            
            // Clear current options except the first empty one
            const $firstOption = $select.find('option:first');
            $select.empty();
            if ($firstOption.val() === '') {
                $select.append($firstOption);
                hasVisibleOptions = true;
            }
            
            // Filter and add matching options
            originalOptions.each(function() {
                const $option = $(this);
                const optionText = $option.text().toLowerCase();
                
                if (optionText.includes(filterValue) || $option.val() === '') {
                    if (!($option.val() === '' && $select.find('option[value=""]').length > 0)) {
                        $select.append($option.clone());
                        hasVisibleOptions = true;
                    }
                }
            });
            
            // Show/hide no results message
            let $noResults = $dropdown.find('.no-results-message');
            if (!hasVisibleOptions && filterValue !== '') {
                if ($noResults.length === 0) {
                    $noResults = $('<div class="no-results-message p-2 text-muted small">' + settings.noResultsText + '</div>');
                    $filterContainer.after($noResults);
                }
                $noResults.show();
            } else {
                $noResults.hide();
            }
        });
        
        // Focus on filter when select is clicked
        $select.on('focus', function() {
            $filterInput.focus();
        });
        
        // Prevent issues with form submission
        $filterInput.on('click', function(e) {
            e.stopPropagation();
        });
    }
    
    // 🆕 FUNCTION FOR BOOTSTRAP DROPDOWNS (your existing code)
    function initBootstrapDropdown($dropdown, $menu, settings) {
        const $items = $menu.find('.dropdown-item');
        
        // Add filter input
        const $filterContainer = $('<div class="dropdown-filter-container p-2 border-bottom"></div>');
        const $filterInput = $('<input type="text" class="form-control form-control-sm" placeholder="' + settings.filterPlaceholder + '">');
        
        $filterContainer.append($filterInput);
        $menu.prepend($filterContainer);
        
        // Add scrollable container
        const $scrollContainer = $('<div class="dropdown-scroll-container"></div>');
        $scrollContainer.css('max-height', settings.maxHeight);
        $scrollContainer.css('overflow-y', 'auto');
        
        $items.wrapAll($scrollContainer);
        
        // Auto-focus on dropdown show
        if (settings.autoFocus) {
            $dropdown.on('shown.bs.dropdown', function() {
                $filterInput.focus();
            });
        }
        
        // Filter functionality
        $filterInput.on('input', function() {
            const filterValue = $(this).val().toLowerCase();
            let visibleCount = 0;
            
            $items.each(function() {
                const $item = $(this);
                const text = $item.text().toLowerCase();
                
                if (text.includes(filterValue)) {
                    $item.show();
                    visibleCount++;
                } else {
                    $item.hide();
                }
            });
            
            // Show/hide no results message
            let $noResults = $menu.find('.no-results-message');
            if (visibleCount === 0 && filterValue !== '') {
                if ($noResults.length === 0) {
                    $noResults = $('<div class="dropdown-item-text text-muted no-results-message">' + settings.noResultsText + '</div>');
                    $menu.append($noResults);
                }
                $noResults.show();
            } else {
                $noResults.hide();
            }
        });
        
        // Prevent dropdown close on filter input click
        $filterInput.on('click', function(e) {
            e.stopPropagation();
        });
    }
    
    // Auto-initialize dropdowns with data-filter attribute
    $(document).ready(function() {
        $('.dropdown[data-filter="true"]').dropdownFilter();
    });
    
})(jQuery);
