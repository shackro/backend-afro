from rest_framework import serializers
from .models import TeamCommission, TeamStats, TeamLevel, TeamTree
from apps.accounts.serializers import UserSerializer


class TeamCommissionSerializer(serializers.ModelSerializer):
    from_user_details = UserSerializer(source='from_user', read_only=True)
    investment_details = serializers.SerializerMethodField()
    base_currency = serializers.SerializerMethodField()

    class Meta:
        model = TeamCommission
        fields = [
            'id', 'user', 'from_user', 'from_user_details',
            'investment', 'investment_details', 'level',
            'amount', 'percentage', 'status', 'paid_date',
            'base_currency', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_investment_details(self, obj):
        from apps.investments.serializers import InvestmentSerializer
        return InvestmentSerializer(obj.investment).data

    def get_base_currency(self, obj):
        return 'USD'


class TeamStatsSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    base_currency = serializers.SerializerMethodField()

    class Meta:
        model = TeamStats
        fields = [
            'id', 'user', 'user_details',
            'total_referrals', 'level_1_count', 'level_2_count', 'level_3_count',
            'active_referrals',
            'level_1_volume', 'level_2_volume', 'level_3_volume',
            'team_volume', 'personal_volume',
            'total_commission_earned', 'pending_commission',
            'level_1_commission', 'level_2_commission', 'level_3_commission',
            'total_bonus_earned', 'bonus_count',  # Add these
            'current_level', 'base_currency', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']

    def get_base_currency(self, obj):
        return 'USD'


class TeamLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamLevel
        fields = '__all__'


class TeamTreeSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    ancestor_details = UserSerializer(source='ancestor', read_only=True)

    class Meta:
        model = TeamTree
        fields = ['id', 'user', 'user_details', 'ancestor', 'ancestor_details', 'depth']