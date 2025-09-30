// C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\static\assets\js\smart_search.js
class SmartSearch {
    constructor(inputElement, dataUrl, options = {}) {
        console.log('🔍 SmartSearch constructor called:', inputElement, dataUrl);
        
        this.input = inputElement;
        this.dataUrl = dataUrl;
        this.options = {
            minLength: 0,
            maxResults: 15,
            placeholder: 'Type to search...',
            allowCreate: false,
            createUrl: null,
            displayField: 'name',
            valueField: 'id',
            searchFields: ['name', 'email', 'phone'],
            ...options
        };
        
        this.dropdown = null;
        this.cache = new Map();
        this.selectedIndex = -1;
        this.isOpen = false;
        this.init();
    }
    
    init() {
        console.log('🚀 Initializing SmartSearch for:', this.input.id || this.input.name);
        
        this.input.setAttribute('autocomplete', 'off');
        this.input.placeholder = this.options.placeholder;
        
        // Create dropdown container
        this.createDropdown();
        
        // Event listeners
        this.input.addEventListener('input', this.debounce(this.handleInput.bind(this), 300));
        this.input.addEventListener('focus', this.handleFocus.bind(this));
        this.input.addEventListener('blur', this.handleBlur.bind(this));
        this.input.addEventListener('keydown', this.handleKeydown.bind(this));
        
        document.addEventListener('click', this.handleDocumentClick.bind(this));
        
        console.log('✅ SmartSearch initialized successfully');
    }
    
    createDropdown() {
        console.log('📦 Creating dropdown...');
        
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'smart-search-dropdown';
        this.dropdown.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 8px 8px;
            max-height: 300px;
            overflow-y: auto;
            z-index: 1050;
            display: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        // Make sure parent has relative positioning
        const parent = this.input.parentNode;
        const parentStyle = window.getComputedStyle(parent);
        if (parentStyle.position === 'static') {
            parent.style.position = 'relative';
        }
        
        parent.appendChild(this.dropdown);
        console.log('✅ Dropdown created and appended');
    }
    
    async handleInput(event) {
        const query = event.target.value.trim();
        console.log('📝 Input changed:', query);
        
        if (query.length === 0) {
            this.loadAllItems();
            return;
        }
        
        if (query.length < this.options.minLength) {
            this.hideDropdown();
            return;
        }
        
        await this.performSearch(query);
    }
    
    async performSearch(query) {
        console.log('🔍 Performing search for:', query);
        
        // Check cache first
        const cacheKey = query.toLowerCase();
        if (this.cache.has(cacheKey)) {
            console.log('💾 Using cached results');
            this.showResults(this.cache.get(cacheKey), query);
            return;
        }
        
        try {
            const url = `${this.dataUrl}?q=${encodeURIComponent(query)}&limit=${this.options.maxResults}`;
            console.log('🌐 Fetching from:', url);
            
            const response = await fetch(url);
            console.log('📡 Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📊 API Response:', data);
            
            // Cache results
            this.cache.set(cacheKey, data.results || data);
            this.showResults(data.results || data, query);
            
        } catch (error) {
            console.error('❌ Search error:', error);
            this.showError('Search failed. Please try again.');
        }
    }
    
    async loadAllItems() {
        console.log('📋 Loading all items...');
        
        const cacheKey = '__all__';
        if (this.cache.has(cacheKey)) {
            console.log('💾 Using cached all items');
            this.showResults(this.cache.get(cacheKey));
            return;
        }
        
        try {
            const url = `${this.dataUrl}?all=1&limit=50`;
            console.log('🌐 Fetching all items from:', url);
            
            const response = await fetch(url);
            console.log('📡 Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📊 All items response:', data);
            
            this.cache.set(cacheKey, data.results || data);
            this.showResults(data.results || data);
            
        } catch (error) {
            console.error('❌ Load all items error:', error);
            this.showError('Failed to load items.');
        }
    }
    
    handleFocus(event) {
        console.log('🎯 Input focused');
        if (this.input.value.trim() === '') {
            this.loadAllItems();
        } else {
            this.performSearch(this.input.value.trim());
        }
    }
    
    handleBlur(event) {
        console.log('😴 Input blurred');
        // Delay hiding to allow for clicks
        setTimeout(() => {
            if (!this.dropdown.matches(':hover')) {
                this.hideDropdown();
            }
        }, 200);
    }
    
    showResults(results, query = '') {
        console.log('📋 Showing results:', results?.length || 0, 'items');
        
        if (!results || results.length === 0) {
            if (this.options.allowCreate && query && query.length >= 2) {
                this.showCreateOption(query);
            } else {
                this.showNoResults();
            }
            return;
        }
        
        this.dropdown.innerHTML = '';
        this.selectedIndex = -1;
        
        // Show results
        results.slice(0, this.options.maxResults).forEach((item, index) => {
            const option = this.createOptionElement(item, query);
            this.dropdown.appendChild(option);
        });
        
        // Add "Create New" option if enabled
        if (this.options.allowCreate && query && query.length >= 2) {
            const createOption = this.createNewOption(query);
            this.dropdown.appendChild(createOption);
        }
        
        this.showDropdown();
    }
    
    createOptionElement(item, query = '') {
        const option = document.createElement('div');
        option.className = 'smart-search-option';
        option.style.cssText = `
            padding: 12px 16px;
            cursor: pointer;
            border-bottom: 1px solid #f0f0f0;
            transition: background-color 0.2s ease;
        `;
        
        // Build display content
        let displayName = item[this.options.displayField] || item.name || 'Unnamed';
        if (query) {
            displayName = this.highlightMatch(displayName, query);
        }
        
        let content = `<div class="fw-bold text-dark">${displayName}</div>`;
        
        // Add secondary information
        const secondaryInfo = [];
        if (item.email) secondaryInfo.push(`📧 ${item.email}`);
        if (item.phone) secondaryInfo.push(`📞 ${item.phone}`);
        if (item.company) secondaryInfo.push(`🏢 ${item.company}`);
        if (item.customer_type) secondaryInfo.push(`👤 ${item.customer_type}`);
        
        if (secondaryInfo.length > 0) {
            content += `<div class="small text-muted mt-1">${secondaryInfo.join(' • ')}</div>`;
        }
        
        // Add balance or additional info
        if (item.balance !== undefined) {
            const balanceClass = parseFloat(item.balance) >= 0 ? 'text-success' : 'text-danger';
            content += `<div class="small ${balanceClass} mt-1 fw-bold">Balance: ${item.balance}</div>`;
        }
        
        option.innerHTML = content;
        
        // Event listeners
        option.addEventListener('click', () => this.selectOption(item));
        option.addEventListener('mouseenter', () => {
            this.selectedIndex = Array.from(this.dropdown.children).indexOf(option);
            this.highlightOption(this.selectedIndex);
        });
        
        return option;
    }
    
    createNewOption(query) {
        const option = document.createElement('div');
        option.className = 'smart-search-option create-option';
        option.style.cssText = `
            padding: 12px 16px;
            cursor: pointer;
            border-top: 2px solid #007bff;
            background-color: #f8f9ff;
            color: #007bff;
            font-weight: 500;
        `;
        
        option.innerHTML = `
            <div class="d-flex align-items-center">
                <span style="margin-right: 8px;">➕</span>
                Create new: "${query}"
            </div>
        `;
        
        option.addEventListener('click', () => this.createNew(query));
        
        return option;
    }
    
    showCreateOption(query) {
        this.dropdown.innerHTML = '';
        const createOption = this.createNewOption(query);
        this.dropdown.appendChild(createOption);
        this.showDropdown();
    }
    
    showNoResults() {
        this.dropdown.innerHTML = `
            <div class="text-center py-3 text-muted">
                <div style="font-size: 1.5em;">🔍</div>
                <div class="mt-1">No results found</div>
            </div>
        `;
        this.showDropdown();
    }
    
    showError(message) {
        this.dropdown.innerHTML = `
            <div class="text-center py-3 text-danger">
                <div style="font-size: 1.5em;">⚠️</div>
                <div class="mt-1">${message}</div>
            </div>
        `;
        this.showDropdown();
    }
    
    highlightMatch(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${this.escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<mark style="background-color: #fff3cd; padding: 1px 3px; border-radius: 3px;">$1</mark>');
    }
    
    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    highlightOption(index) {
        const options = this.dropdown.querySelectorAll('.smart-search-option');
        options.forEach((opt, i) => {
            if (i === index) {
                opt.style.backgroundColor = '#e3f2fd';
            } else {
                opt.style.backgroundColor = '';
            }
        });
    }
    
    selectOption(item) {
        console.log('✅ Selecting option:', item);
        
        this.input.value = item[this.options.displayField] || item.name;
        this.input.dataset.selectedId = item[this.options.valueField] || item.id;
        
        // Update hidden field if exists
        const hiddenFieldName = this.input.name.replace('_search', '');
        const hiddenField = document.querySelector(`input[name="${hiddenFieldName}"]`);
        if (hiddenField) {
            hiddenField.value = item[this.options.valueField] || item.id;
            console.log('✅ Updated hidden field:', hiddenFieldName, '=', hiddenField.value);
        }
        
        // Trigger custom event
        this.input.dispatchEvent(new CustomEvent('smartselect', {
            detail: { item, field: this.input }
        }));
        
        this.hideDropdown();
    }
    
    async createNew(name) {
        if (!this.options.createUrl) return;
        
        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            const response = await fetch(this.options.createUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken ? csrfToken.value : ''
                },
                body: JSON.stringify({ name: name.trim() })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.selectOption(data.item);
                // Clear cache to refresh data
                this.cache.clear();
            } else {
                console.error('Create error:', data.error);
                alert('Error creating item: ' + data.error);
            }
            
        } catch (error) {
            console.error('Create new item error:', error);
            alert('Error creating item. Please try again.');
        }
    }
    
    showDropdown() {
        console.log('👁️ Showing dropdown');
        this.dropdown.style.display = 'block';
        this.isOpen = true;
    }
    
    hideDropdown() {
        console.log('👁️‍🗨️ Hiding dropdown');
        this.dropdown.style.display = 'none';
        this.isOpen = false;
        this.selectedIndex = -1;
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    handleKeydown(event) {
        if (!this.isOpen) return;
        
        const options = this.dropdown.querySelectorAll('.smart-search-option:not(.create-option)');
        
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, options.length - 1);
                this.highlightOption(this.selectedIndex);
                break;
                
            case 'ArrowUp':
                event.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.highlightOption(this.selectedIndex);
                break;
                
            case 'Enter':
                event.preventDefault();
                if (this.selectedIndex >= 0 && options[this.selectedIndex]) {
                    options[this.selectedIndex].click();
                }
                break;
                
            case 'Escape':
                this.hideDropdown();
                break;
        }
    }
    
    handleDocumentClick(event) {
        if (!this.input.contains(event.target) && !this.dropdown.contains(event.target)) {
            this.hideDropdown();
        }
    }
}

// Make SmartSearch available globally - NO DUPLICATE INITIALIZATION
window.SmartSearch = SmartSearch;

// Simple logging to confirm script loaded
console.log('✅ SmartSearch class loaded and available globally');