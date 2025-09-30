# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\journal\admin.py

from django.contrib import admin
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError

from .models import JournalEntry, JournalEntryLine

# This is the new, more robust validation logic
class JournalEntryLineInlineFormSet(BaseInlineFormSet):
    def clean(self):
        """
        Custom validation for the inline formset to ensure debits equal credits.
        """
        # First, run the parent's clean method
        super().clean()

        # If any errors have already occurred in individual forms, we can stop.
        if any(self.errors):
            return

        # Now, calculate totals from the cleaned_data of the formset
        total_debit = 0
        total_credit = 0
        line_count = 0

        # self.cleaned_data is a list of dictionaries, one for each valid form
        for data in self.cleaned_data:
            # Check if the form is not empty and not marked for deletion
            if data and not data.get('DELETE', False):
                line_count += 1
                debit = data.get('debit', 0) or 0
                credit = data.get('credit', 0) or 0
                total_debit += debit
                total_credit += credit

        # Only perform validation if there is at least one valid line
        if line_count > 0:
            if total_debit != total_credit:
                # This error will now correctly appear just above the lines
                raise ValidationError('The total debits must equal the total credits.')

            if total_debit == 0: # This implies credits are also 0
                raise ValidationError('The journal entry cannot have a total of zero.')


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    # Use the custom formset we defined above
    formset = JournalEntryLineInlineFormSet
    extra = 2 # Show 2 empty forms by default


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'description', 'company')
    list_filter = ('company', 'date')
    search_fields = ('description',)
    inlines = [JournalEntryLineInline]
    date_hierarchy = 'date'
