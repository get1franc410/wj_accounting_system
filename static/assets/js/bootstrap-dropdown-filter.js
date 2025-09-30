// C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\static\assets\js\bootstrap-dropdown-filter.js
(function($) {
    'use strict';
    
    $.fn.dropdownFilter = function(options) {
        const settings = $.extend({
            filterPlaceholder: 'Search...',
            noResultsText: 'No results found',
            autoFocus: true,
            maxHeight: '250px'
        }, options);
        
        return this.each(function() {
            const $dropdownContainer = $(this);
            
            // FIX: Detect if we are working with a <select> element or a Bootstrap dropdown
            const $select = $dropdownContainer.is('select') ? $dropdownContainer : $dropdownContainer.find('select');
            const $menu = $dropdownContainer.find('.dropdown-menu');
            
            if ($select.length > 0) {
                // Handle standard <select> elements
                initSelectDropdown($dropdownContainer, $select, settings);
            } else if ($menu.length > 0) {
                // Handle Bootstrap dropdown menus
                initBootstrapDropdown($dropdownContainer, $menu, settings);
            }
        });
    };
    
    // NEW: Function to handle filtering for <select> elements
    function initSelectDropdown($container, $select, settings) {
        if ($container.data('dropdown-filter-initialized')) return;
        $container.data('dropdown-filter-initialized', true);

        // Create filter input and wrap elements
        const $wrapper = $('<div class="dropdown-filter-wrapper"></div>');
        const $filterInput = $('<input type="text" class="form-control form-control-sm dropdown-filter-input mb-1" placeholder="' + settings.filterPlaceholder + '">');
        const $noResults = $('<div class="no-results-message p-2 text-muted small" style="display:none;">' + settings.noResultsText + '</div>');

        $select.wrap($wrapper).before($filterInput).after($noResults);
        
        $select.css({
            'max-height': settings.maxHeight,
            'overflow-y': 'auto'
        });
        
        // Store original options
        const originalOptions = $select.find('option').clone();
        
        $filterInput.on('input', function() {
            const filterValue = $(this).val().toLowerCase();
            let hasVisibleOptions = false;
            
            // Filter options directly in the select
            $select.find('option').each(function() {
                const $option = $(this);
                if ($option.val() === '') { // Always show placeholder
                    $option.show();
                    return;
                }
                const optionText = $option.text().toLowerCase();
                if (optionText.includes(filterValue)) {
                    $option.show();
                    hasVisibleOptions = true;
                } else {
                    $option.hide();
                }
            });
            
            $noResults.toggle(!hasVisibleOptions && filterValue !== '');
        });
    }
    
    // Your existing function for Bootstrap dropdowns
    function initBootstrapDropdown($dropdown, $menu, settings) {
        if ($dropdown.data('dropdown-filter-initialized')) return;
        $dropdown.data('dropdown-filter-initialized', true);

        const $items = $menu.find('.dropdown-item');
        const $filterContainer = $('<div class="dropdown-filter-container p-2 border-bottom"></div>');
        const $filterInput = $('<input type="text" class="form-control form-control-sm" placeholder="' + settings.filterPlaceholder + '">');
        
        $filterContainer.append($filterInput);
        $menu.prepend($filterContainer);
        
        const $scrollContainer = $('<div class="dropdown-scroll-container"></div>').css({
            'max-height': settings.maxHeight,
            'overflow-y': 'auto'
        });
        
        $items.wrapAll($scrollContainer);
        
        if (settings.autoFocus) {
            $dropdown.on('shown.bs.dropdown', () => $filterInput.focus());
        }
        
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
        
        $filterInput.on('click', e => e.stopPropagation());
    }
    
    // Auto-initialize elements with data-filter attribute
    $(document).ready(function() {
        // Target both Bootstrap dropdowns and select elements
        $('.dropdown[data-filter="true"], select[data-filter="true"]').dropdownFilter();
    });
    
})(jQuery);
