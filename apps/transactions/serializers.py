from decimal import Decimal
from rest_framework import serializers
from .models import Transaction, PaymentMethod, WithdrawalRequest
from apps.accounts.serializers import UserSerializer


class TransactionSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['id', 'reference', 'requested_at', 'processed_at', 'completed_at']


class CreateDepositSerializer(serializers.Serializer):
    # Minimum deposit amounts
    MIN_DEPOSIT_USD = 3.50  # Approximately 450 KES
    MIN_DEPOSIT_KES = 450
    MIN_DEPOSIT_EUR = 3.20  # Approximately 450 KES equivalent

    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01') )
    currency = serializers.ChoiceField(choices=['USD', 'KES', 'EUR'], default='USD')
    payment_method = serializers.ChoiceField(choices=Transaction.PAYMENT_METHODS)

    # Conditional fields based on payment method
    bank_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    account_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    account_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    swift_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    mpesa_phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    crypto_address = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_amount(self, value):
        """Validate minimum deposit amount based on currency"""
        # Convert to float for comparison
        amount = float(value)

        # Get currency from data (default to USD if not provided)
        currency = self.initial_data.get('currency', 'USD')

        if currency == 'KES':
            if amount < self.MIN_DEPOSIT_KES:
                raise serializers.ValidationError(
                    f"Minimum deposit amount is {self.MIN_DEPOSIT_KES} KES"
                )
        elif currency == 'EUR':
            if amount < self.MIN_DEPOSIT_EUR:
                raise serializers.ValidationError(
                    f"Minimum deposit amount is {self.MIN_DEPOSIT_EUR} EUR"
                )
        else:  # USD
            if amount < self.MIN_DEPOSIT_USD:
                raise serializers.ValidationError(
                    f"Minimum deposit amount is ${self.MIN_DEPOSIT_USD} USD"
                )

        return value

    def validate(self, data):
        payment_method = data.get('payment_method')

        if payment_method == 'bank_transfer':
            if not data.get('bank_name'):
                raise serializers.ValidationError({"bank_name": "Bank name is required"})
            if not data.get('account_number'):
                raise serializers.ValidationError({"account_number": "Account number is required"})
            if not data.get('account_name'):
                raise serializers.ValidationError({"account_name": "Account name is required"})

        elif payment_method == 'mpesa':
            if not data.get('mpesa_phone'):
                raise serializers.ValidationError({"mpesa_phone": "Phone number is required"})

        elif payment_method == 'crypto':
            if not data.get('crypto_address'):
                raise serializers.ValidationError({"crypto_address": "Crypto address is required"})

        return data


class CreateWithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=1)
    currency = serializers.ChoiceField(choices=['USD', 'KES', 'EUR'], default='USD')
    payment_method = serializers.ChoiceField(choices=Transaction.PAYMENT_METHODS)

    # Conditional fields based on payment method
    bank_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    account_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    account_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    swift_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    mpesa_phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    crypto_address = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_amount(self, value):
        user = self.context['request'].user
        if value > user.available_balance:
            raise serializers.ValidationError("Insufficient balance")
        return value

    def validate(self, data):
        payment_method = data.get('payment_method')

        if payment_method == 'bank_transfer':
            if not data.get('bank_name'):
                raise serializers.ValidationError({"bank_name": "Bank name is required"})
            if not data.get('account_number'):
                raise serializers.ValidationError({"account_number": "Account number is required"})
            if not data.get('account_name'):
                raise serializers.ValidationError({"account_name": "Account name is required"})

        elif payment_method == 'mpesa':
            if not data.get('mpesa_phone'):
                raise serializers.ValidationError({"mpesa_phone": "Phone number is required"})

        elif payment_method == 'crypto':
            if not data.get('crypto_address'):
                raise serializers.ValidationError({"crypto_address": "Crypto address is required"})

        return data


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at']


class TransactionSummarySerializer(serializers.Serializer):
    total_deposits = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_withdrawals = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_deposits = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_withdrawals = serializers.DecimalField(max_digits=15, decimal_places=2)
    recent_transactions = TransactionSerializer(many=True)