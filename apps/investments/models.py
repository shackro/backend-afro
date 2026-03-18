from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from apps.accounts.models import User
from apps.products.models import Product
import uuid


class Investment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='investments')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    daily_income = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    last_payout_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Financial tracking
    total_expected_return = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    total_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    remaining_payouts = models.IntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.name} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timezone.timedelta(days=self.product.validity_period)
        if not self.total_expected_return:
            self.total_expected_return = self.daily_income * self.product.validity_period
        if not self.remaining_payouts:
            self.remaining_payouts = self.product.validity_period
        super().save(*args, **kwargs)

    @property
    def days_remaining(self):
        if self.status != 'active':
            return 0
        now = timezone.now()
        if now >= self.end_date:
            return 0
        return (self.end_date - now).days

    @property
    def progress_percentage(self):
        if self.status != 'active':
            return 0
        total_days = self.product.validity_period
        days_passed = (timezone.now() - self.start_date).days
        return min(100, (days_passed / total_days) * 100)

    @property
    def earned_so_far(self):
        if self.status != 'active':
            return self.total_paid
        days_passed = (timezone.now() - self.start_date).days
        expected = min(days_passed * self.daily_income, self.total_expected_return)
        return min(expected, self.total_expected_return)


class InvestmentTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('investment', 'Investment'),
        ('daily_payout', 'Daily Payout'),
        ('commission', 'Commission'),
        ('withdrawal', 'Withdrawal'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='investment_transactions')  # Changed from 'transactions'

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.transaction_type} - {self.amount}"