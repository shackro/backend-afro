from django.db import models
from django.core.validators import MinValueValidator
from apps.accounts.models import User
import uuid


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHODS = [
        ('bank_transfer', 'Bank Transfer'),
        ('mpesa', 'M-Pesa'),
        ('credit_card', 'Credit Card'),
        ('crypto', 'Cryptocurrency'),
        ('paypal', 'PayPal'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)

    # Transaction details
    reference = models.CharField(max_length=100, unique=True, editable=False)
    description = models.TextField(blank=True)

    # Payment provider details
    provider_reference = models.CharField(max_length=100, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)

    # Bank details (for bank transfers)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    account_name = models.CharField(max_length=100, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)

    # M-Pesa details
    mpesa_phone = models.CharField(max_length=15, blank=True)
    mpesa_receipt = models.CharField(max_length=50, blank=True)

    # Crypto details
    crypto_address = models.CharField(max_length=255, blank=True)
    crypto_tx_hash = models.CharField(max_length=255, blank=True)

    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)


    # Admin notes
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.user.email} - {self.transaction_type} - {self.amount} {self.currency}"


class PaymentMethod(models.Model):
    """User's saved payment methods"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=20, choices=Transaction.PAYMENT_METHODS)
    is_default = models.BooleanField(default=False)

    # Bank details
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    account_name = models.CharField(max_length=100, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)

    # M-Pesa
    mpesa_phone = models.CharField(max_length=15, blank=True)

    # Crypto
    crypto_address = models.CharField(max_length=255, blank=True)
    crypto_network = models.CharField(max_length=50, blank=True)

    # Credit Card (tokenized)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, blank=True)
    card_token = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', '-created_at']


class WithdrawalRequest(models.Model):
    """Additional details for withdrawal requests"""
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='withdrawal_details')
    user_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reviewed_withdrawals')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)