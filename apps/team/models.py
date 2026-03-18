from django.db import models
from django.core.validators import MinValueValidator
from apps.accounts.models import User
from apps.investments.models import Investment
import uuid


class TeamLevel(models.Model):
    LEVEL_CHOICES = [
        ('B', 'Level B - 10%'),
        ('C', 'Level C - 6%'),
        ('D', 'Level D - 3%'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    level_code = models.CharField(max_length=1, choices=LEVEL_CHOICES, unique=True)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    min_referrals = models.IntegerField(default=0)
    min_team_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['level_code']

    def __str__(self):
        return f"{self.level_code} - {self.commission_percentage}%"


class TeamCommission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commissions_received')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commissions_generated')
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='commissions')

    level = models.CharField(max_length=1, choices=TeamLevel.LEVEL_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    percentage = models.DecimalField(max_digits=5, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'from_user', 'investment', 'level']

    def __str__(self):
        return f"{self.user.email} - Level {self.level} - {self.amount}"


class TeamStats(models.Model):
    LEVEL_CHOICES = [
        ('B', 'Level B - 10%'),
        ('C', 'Level C - 6%'),
        ('D', 'Level D - 3%'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='team_stats')

    # Team metrics
    total_referrals = models.IntegerField(default=0)  # Direct referrals only
    level_1_count = models.IntegerField(default=0)  # Direct referrals
    level_2_count = models.IntegerField(default=0)  # Referrals of referrals
    level_3_count = models.IntegerField(default=0)  # Third level

    active_referrals = models.IntegerField(default=0)

    # Volume metrics by level
    level_1_volume = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    level_2_volume = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    level_3_volume = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    team_volume = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    personal_volume = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # Commission metrics
    total_commission_earned = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    pending_commission = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    level_1_commission = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    level_2_commission = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    level_3_commission = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # Add to TeamStats model
    total_bonus_earned = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    bonus_count = models.IntegerField(default=0)

    # Level metrics
    current_level = models.CharField(max_length=1, choices=LEVEL_CHOICES, default='B')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-team_volume']

    def __str__(self):
        return f"{self.user.email} - Level {self.current_level}"


class TeamTree(models.Model):
    """Store the team hierarchy for efficient querying"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_nodes')
    ancestor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_descendants')
    depth = models.IntegerField()  # 1 = direct referral, 2 = level 2, 3 = level 3

    class Meta:
        unique_together = ['user', 'ancestor']
        indexes = [
            models.Index(fields=['ancestor', 'depth']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        level_name = {1: 'Direct', 2: 'Level 2', 3: 'Level 3'}.get(self.depth, f'Level {self.depth}')
        return f"{self.ancestor.email} -> {self.user.email} ({level_name})"