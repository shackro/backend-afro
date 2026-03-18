# backend/apps/products/serializers.py

from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    total_return = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    roi_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    daily_roi_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    # Include calculated commissions
    b_commission = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    c_commission = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    d_commission = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    # Add commission percentages for frontend display
    commission_percentages = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'daily_income', 'validity_period',
            'b_commission', 'c_commission', 'd_commission',
            'commission_percentages', 'description', 'min_investment',
            'max_investment', 'is_active', 'image', 'total_return',
            'roi_percentage', 'daily_roi_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_commission_percentages(self, obj):
        """Return the fixed commission percentages"""
        return {
            'level_1': float(obj.COMMISSION_LEVEL_1 * 100),
            'level_2': float(obj.COMMISSION_LEVEL_2 * 100),
            'level_3': float(obj.COMMISSION_LEVEL_3 * 100),
        }