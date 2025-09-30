# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\core\mixins.py
from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView
from decimal import Decimal

class SmartFormMixin:
    """Mixin to automatically group form fields and determine sizing"""
    
    def get_form_sections(self, form):
        """Auto-group form fields into logical sections"""
        sections = []
        
        # Define field groupings based on field names and types
        field_groups = {
            'basic_info': {
                'title': 'Basic Information',
                'fields': ['name', 'title', 'description', 'sku', 'reference_number'],
                'priority': 1
            },
            'financial': {
                'title': 'Financial Details',
                'fields': ['amount', 'price', 'cost', 'total', 'balance', 'credit_limit'],
                'priority': 2
            },
            'dates': {
                'title': 'Dates & Timing',
                'fields': ['date', 'due_date', 'start_date', 'end_date', 'created_at'],
                'priority': 3
            },
            'contact': {
                'title': 'Contact Information',
                'fields': ['email', 'phone', 'address', 'website'],
                'priority': 4
            },
            'accounts': {
                'title': 'Account Configuration',
                'fields': ['account', 'account_type', 'income_account', 'expense_account'],
                'priority': 5
            },
            'settings': {
                'title': 'Settings & Options',
                'fields': ['is_active', 'is_enabled', 'currency', 'method', 'type'],
                'priority': 6
            }
        }
        
        # Auto-assign fields to groups
        assigned_fields = set()
        
        for group_key, group_info in sorted(field_groups.items(), key=lambda x: x[1]['priority']):
            group_fields = []
            
            for field_name, field in form.fields.items():
                if field_name in assigned_fields:
                    continue
                    
                # Check if field belongs to this group
                if any(keyword in field_name.lower() for keyword in group_info['fields']):
                    field.col_size = self.get_field_column_size(field)
                    group_fields.append(field)
                    assigned_fields.add(field_name)
            
            if group_fields:
                sections.append({
                    'title': group_info['title'],
                    'fields': group_fields
                })
        
        # Add remaining fields to "Other" section
        remaining_fields = []
        for field_name, field in form.fields.items():
            if field_name not in assigned_fields:
                field.col_size = self.get_field_column_size(field)
                remaining_fields.append(field)
        
        if remaining_fields:
            sections.append({
                'title': 'Additional Information',
                'fields': remaining_fields
            })
        
        return sections
    
    def get_field_column_size(self, field):
        """Determine column size based on field type and widget"""
        if isinstance(field.widget, forms.Textarea):
            return 12  # Full width for text areas
        elif isinstance(field.widget, forms.CheckboxInput):
            return 3   # Small for checkboxes
        elif isinstance(field.widget, forms.DateInput):
            return 4   # Medium for dates
        elif isinstance(field.widget, forms.NumberInput):
            return 4   # Medium for numbers
        elif isinstance(field.widget, forms.Select):
            return 6   # Half width for selects
        else:
            return 6   # Default half width
