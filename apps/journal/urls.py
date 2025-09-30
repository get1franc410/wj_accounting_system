# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\journal\urls.py
from django.urls import path
from .views import JournalEntryListView, JournalEntryCreateView, JournalEntryDetailView
from . import views

app_name = 'journal'

urlpatterns = [
    path('', JournalEntryListView.as_view(), name='journal-entry-list'),
    path('create/', JournalEntryCreateView.as_view(), name='journal-entry-create'),
    path('<int:pk>/', JournalEntryDetailView.as_view(), name='journal-entry-detail'),
    path('delete/<int:pk>/', views.JournalEntryDeleteView.as_view(), name='journal-entry-delete'),
    
    # Export URLs
    path('export/', views.export_journal_entries, name='export'),
]

