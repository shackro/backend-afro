from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
import uuid


class User(AbstractUser):
    """Custom User model for Afro Connect"""

    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('KES', 'Kenyan Shilling'),
        ('EUR', 'Euro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    referral_code = models.CharField(max_length=10, unique=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')

    # Currency preference
    preferred_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        help_text="User's preferred currency for displaying amounts"
    )

    # Wallet information (always stored in USD as base currency)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_invested = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_earned = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_withdrawn = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Add to User model
    total_bonus_earned = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                             validators=[MinValueValidator(0)])
    bonus_count = models.IntegerField(default=0)  # Number of sign-up bonuses received

    # KYC information
    is_kyc_verified = models.BooleanField(default=False)
    id_document = models.FileField(upload_to='kyc/', null=True, blank=True)
    id_document_type = models.CharField(max_length=20, choices=[
        ('passport', 'Passport'),
        ('national_id', 'National ID'),
        ('drivers_license', 'Driver\'s License'),
    ], blank=True)

    # Account status
    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} - {self.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        super().save(*args, **kwargs)

    def generate_referral_code(self):
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not User.objects.filter(referral_code=code).exists():
                return code

    @property
    def referral_link(self):
        return f"https://afroconnect.com/register?ref={self.referral_code}"

    @property
    def referral_count(self):
        return self.referrals.count()

    @property
    def available_balance(self):
        """Balance available for withdrawal (considering pending investments)"""
        from apps.investments.models import Investment
        pending_investments = Investment.objects.filter(
            user=self,
            status='active'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        return self.balance - pending_investments


class UserProfile(models.Model):
    """Additional user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    notification_preferences = models.JSONField(default=dict)
    two_factor_enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ['user']

    def __str__(self):
        return f"Profile for {self.user.email}"