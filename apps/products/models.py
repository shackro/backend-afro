# backend/apps/products/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


class Product(models.Model):
    """Investment Product Model"""

    # Fixed commission percentages
    COMMISSION_LEVEL_1 = Decimal('0.10')  # 10%
    COMMISSION_LEVEL_2 = Decimal('0.06')  # 6%
    COMMISSION_LEVEL_3 = Decimal('0.03')  # 3%

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    daily_income = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    validity_period = models.IntegerField(validators=[MinValueValidator(1)])  # days

    description = models.TextField(blank=True)
    min_investment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_investment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return self.name

    @property
    def total_return(self):
        """Calculate total return over the validity period"""
        if not self.daily_income or not self.validity_period:
            return Decimal('0')
        return self.daily_income * self.validity_period

    @property
    def roi_percentage(self):
        """Calculate ROI percentage"""
        if not self.price or self.price == 0:
            return Decimal('0')
        total_return = self.total_return
        return ((total_return - self.price) / self.price) * 100

    @property
    def daily_roi_percentage(self):
        """Calculate daily ROI percentage"""
        if not self.price or self.price == 0:
            return Decimal('0')
        return (self.daily_income / self.price) * 100

    # Commission properties - automatically calculated with null checks
    @property
    def b_commission(self):
        """Level 1 (10%) commission - calculated from daily income"""
        if not self.daily_income:
            return Decimal('0')
        return self.daily_income * self.COMMISSION_LEVEL_1

    @property
    def c_commission(self):
        """Level 2 (6%) commission - calculated from daily income"""
        if not self.daily_income:
            return Decimal('0')
        return self.daily_income * self.COMMISSION_LEVEL_2

    @property
    def d_commission(self):
        """Level 3 (3%) commission - calculated from daily income"""
        if not self.daily_income:
            return Decimal('0')
        return self.daily_income * self.COMMISSION_LEVEL_3

    def get_commissions(self):
        """Return all commissions as a dictionary"""
        return {
            'level_1': {
                'percentage': float(self.COMMISSION_LEVEL_1 * 100),
                'amount': float(self.b_commission)
            },
            'level_2': {
                'percentage': float(self.COMMISSION_LEVEL_2 * 100),
                'amount': float(self.c_commission)
            },
            'level_3': {
                'percentage': float(self.COMMISSION_LEVEL_3 * 100),
                'amount': float(self.d_commission)
            }
        }