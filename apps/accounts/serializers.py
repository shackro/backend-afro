from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, UserProfile
import re


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture', 'date_of_birth', 'address', 'city',
            'country', 'postal_code', 'occupation', 'two_factor_enabled',
            'notification_preferences'
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    referral_link = serializers.ReadOnlyField()
    referral_count = serializers.ReadOnlyField()
    available_balance = serializers.ReadOnlyField()
    preferred_currency = serializers.ChoiceField(choices=User.CURRENCY_CHOICES, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'referral_code', 'referral_link',
            'referral_count', 'referred_by', 'balance', 'total_invested',
            'total_earned', 'total_withdrawn', 'available_balance',
            'is_kyc_verified', 'is_staff', 'profile', 'created_at',
            'preferred_currency',
        ]
        read_only_fields = ['id', 'balance', 'total_invested', 'total_earned',
                            'total_withdrawn', 'created_at', 'referral_code']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8, label='Confirm Password')
    referral_code = serializers.CharField(required=False, allow_blank=True)
    preferred_currency = serializers.ChoiceField(choices=User.CURRENCY_CHOICES, required=False, default='USD')

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2',
                  'first_name', 'last_name', 'phone_number', 'referral_code',
                  'preferred_currency']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match"})

        referral_code = data.get('referral_code')
        if referral_code:
            try:
                User.objects.get(referral_code=referral_code)
            except User.DoesNotExist:
                raise serializers.ValidationError({"referral_code": "Invalid referral code"})

        return data

    def create(self, validated_data):
        referral_code = validated_data.pop('referral_code', None)
        validated_data.pop('password2', None)
        preferred_currency = validated_data.pop('preferred_currency', 'USD')

        referred_by = None
        if referral_code:
            referred_by = User.objects.get(referral_code=referral_code)

        user = User.objects.create_user(
            **validated_data,
            referred_by=referred_by,
            preferred_currency=preferred_currency
        )

        # Create user profile
        UserProfile.objects.create(user=user)

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                username=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid credentials")
        else:
            raise serializers.ValidationError("Must include email and password")

        data['user'] = user
        return data


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'email']

    def validate_email(self, value):
        if User.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_number(self, value):
        if value and not re.match(r'^\+?1?\d{9,15}$', value):
            raise serializers.ValidationError(
                "Phone number must be entered in format: '+999999999'. Up to 15 digits allowed.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords don't match"})
        return data


class UpdateCurrencySerializer(serializers.Serializer):
    preferred_currency = serializers.ChoiceField(choices=User.CURRENCY_CHOICES)

    def update(self, instance, validated_data):
        instance.preferred_currency = validated_data.get('preferred_currency', instance.preferred_currency)
        instance.save()
        return instance


class KYCSerializer(serializers.Serializer):
    id_type = serializers.ChoiceField(choices=['passport', 'national_id', 'drivers_license'])
    id_number = serializers.CharField(max_length=50)
    front_image = serializers.ImageField()
    back_image = serializers.ImageField()
    selfie = serializers.ImageField()


class NotificationPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['notification_preferences']


class TwoFactorSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass