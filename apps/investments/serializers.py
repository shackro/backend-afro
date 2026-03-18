from rest_framework import serializers
from django.core.validators import MinValueValidator
from .models import Investment, InvestmentTransaction
from apps.products.serializers import ProductSerializer


class InvestmentSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    days_remaining = serializers.ReadOnlyField()
    progress_percentage = serializers.ReadOnlyField()
    earned_so_far = serializers.ReadOnlyField()
    base_currency = serializers.SerializerMethodField()

    class Meta:
        model = Investment
        fields = [
            'id', 'user', 'product', 'product_details', 'amount',
            'daily_income', 'start_date', 'end_date', 'last_payout_date',
            'status', 'total_expected_return', 'total_paid',
            'remaining_payouts', 'days_remaining', 'progress_percentage',
            'earned_so_far', 'base_currency', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_base_currency(self, obj):
        return 'USD'


class CreateInvestmentSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])

    def validate(self, data):
        from apps.products.models import Product
        try:
            product = Product.objects.get(id=data['product_id'], is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product_id": "Invalid product"})

        # Check minimum investment (amount is in USD)
        if product.min_investment and data['amount'] < product.min_investment:
            raise serializers.ValidationError(
                {"amount": f"Minimum investment is {product.min_investment}"}
            )

        # Check maximum investment
        if product.max_investment and data['amount'] > product.max_investment:
            raise serializers.ValidationError(
                {"amount": f"Maximum investment is {product.max_investment}"}
            )

        # Check user balance (balance is in USD)
        user = self.context['request'].user
        if user.balance < data['amount']:
            raise serializers.ValidationError(
                {
                    "amount": "Insufficient balance",
                    "available_balance": float(user.balance),
                    "required_amount": float(data['amount']),
                    "shortfall": float(data['amount'] - user.balance)
                }
            )

        data['product'] = product
        return data


class InvestmentTransactionSerializer(serializers.ModelSerializer):
    base_currency = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentTransaction
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_base_currency(self, obj):
        return 'USD'