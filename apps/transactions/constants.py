# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\transactions\constants.py
"""
Single source of truth for all transaction types
"""

class TransactionType:
    """Transaction type constants and utilities"""
    
    # Core transaction types
    SALE = 'SALE'
    PURCHASE = 'PURCHASE'
    EXPENSE = 'EXPENSE'
    PAYMENT = 'PAYMENT'
    TRANSFER = 'TRANSFER'
    ADJUSTMENT = 'ADJUSTMENT'
    
    # Choices for forms and models
    CHOICES = [
        (SALE, 'Sale / Invoice'),
        (PURCHASE, 'Purchase / Bill'),
        (EXPENSE, 'Expense'),
        (PAYMENT, 'Payment Received'), 
        (TRANSFER, 'Transfer'),
        (ADJUSTMENT, 'Adjustment Entry'),
    ]
    
    # Mapping for display purposes
    DISPLAY_MAPPING = dict(CHOICES)
    
    @classmethod
    def get_display_name(cls, transaction_type):
        """Get human-readable name for transaction type"""
        return cls.DISPLAY_MAPPING.get(transaction_type, transaction_type)
    
    @classmethod
    def get_all_types(cls):
        """Get all available transaction types"""
        return [choice[0] for choice in cls.CHOICES]
    
    @classmethod
    def get_recommended_for_account_category(cls, account_category):
        """Get recommended transaction types for account category"""
        recommendations = {
            'ASSET': [cls.PURCHASE, cls.TRANSFER, cls.ADJUSTMENT],
            'LIABILITY': [cls.PURCHASE, cls.PAYMENT, cls.TRANSFER, cls.ADJUSTMENT],
            'EQUITY': [cls.TRANSFER, cls.ADJUSTMENT],
            'REVENUE': [cls.SALE],
            'EXPENSE': [cls.EXPENSE, cls.PURCHASE, cls.ADJUSTMENT],
        }
        return recommendations.get(account_category, [])
