from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import TeamCommission, TeamStats, TeamLevel, TeamTree
from .serializers import (
    TeamCommissionSerializer, TeamStatsSerializer,
    TeamLevelSerializer, TeamTreeSerializer
)
from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from .utils import calculate_team_stats


class TeamCommissionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeamCommissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['level', 'status']
    ordering_fields = ['created_at', 'amount']

    def get_queryset(self):
        return TeamCommission.objects.filter(user=self.request.user)


class TeamStatsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeamStatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TeamStats.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_stats(self, request):
        stats, created = TeamStats.objects.get_or_create(user=request.user)
        # Refresh stats
        stats = calculate_team_stats(request.user)
        serializer = self.get_serializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def level_breakdown(self, request):
        """Get detailed breakdown by level"""
        stats, created = TeamStats.objects.get_or_create(user=request.user)

        # Get team members by level
        level_1_users = TeamTree.objects.filter(
            ancestor=request.user,
            depth=1
        ).select_related('user')

        level_2_users = TeamTree.objects.filter(
            ancestor=request.user,
            depth=2
        ).select_related('user')

        level_3_users = TeamTree.objects.filter(
            ancestor=request.user,
            depth=3
        ).select_related('user')

        return Response({
            'level_1': {
                'count': level_1_users.count(),
                'users': UserSerializer([t.user for t in level_1_users], many=True).data,
                'volume': stats.level_1_volume,
                'commission': stats.level_1_commission
            },
            'level_2': {
                'count': level_2_users.count(),
                'users': UserSerializer([t.user for t in level_2_users], many=True).data,
                'volume': stats.level_2_volume,
                'commission': stats.level_2_commission
            },
            'level_3': {
                'count': level_3_users.count(),
                'users': UserSerializer([t.user for t in level_3_users], many=True).data,
                'volume': stats.level_3_volume,
                'commission': stats.level_3_commission
            }
        })


class TeamViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.none()

    @action(detail=False, methods=['get'])
    def team_tree(self, request):
        """Get complete team tree structure"""
        team_members = TeamTree.objects.filter(
            ancestor=request.user
        ).select_related('user', 'ancestor').order_by('depth')

        serializer = TeamTreeSerializer(team_members, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def team_members(self, request):
        """Get all team members with their level"""
        team_members = TeamTree.objects.filter(
            ancestor=request.user
        ).select_related('user').order_by('depth')

        data = []
        for member in team_members:
            user_data = UserSerializer(member.user).data
            user_data['depth'] = member.depth
            user_data['referral_level'] = {
                1: 'Level 1 (10%)',
                2: 'Level 2 (6%)',
                3: 'Level 3 (3%)'
            }.get(member.depth, f'Level {member.depth}')
            data.append(user_data)

        return Response(data)

    @action(detail=False, methods=['get'])
    def level_1(self, request):
        """Get direct referrals (Level 1 - 10%)"""
        referrals = User.objects.filter(referred_by=request.user)
        serializer = self.get_serializer(referrals, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def level_2(self, request):
        """Get Level 2 referrals (6%)"""
        level_2_users = TeamTree.objects.filter(
            ancestor=request.user,
            depth=2
        ).select_related('user')

        users = [t.user for t in level_2_users]
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def level_3(self, request):
        """Get Level 3 referrals (3%)"""
        level_3_users = TeamTree.objects.filter(
            ancestor=request.user,
            depth=3
        ).select_related('user')

        users = [t.user for t in level_3_users]
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def commissions_summary(self, request):
        """Get summary of commissions by level"""
        commissions = TeamCommission.objects.filter(
            user=request.user
        )

        summary = {
            'total': commissions.aggregate(total=Sum('amount'))['total'] or 0,
            'pending': commissions.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
            'paid': commissions.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0,
        }

        # Breakdown by level
        for level in ['B', 'C', 'D']:
            level_comms = commissions.filter(level=level)
            summary[f'level_{level}_total'] = level_comms.aggregate(total=Sum('amount'))['total'] or 0
            summary[f'level_{level}_count'] = level_comms.count()

        return Response(summary)

    @action(detail=False, methods=['get'])
    def commission_history(self, request):
        """Get commission history with filters"""
        level = request.query_params.get('level')
        status_filter = request.query_params.get('status')

        commissions = TeamCommission.objects.filter(user=request.user)

        if level:
            commissions = commissions.filter(level=level)
        if status_filter:
            commissions = commissions.filter(status=status_filter)

        # Pagination
        page = self.paginate_queryset(commissions)
        if page is not None:
            serializer = TeamCommissionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TeamCommissionSerializer(commissions, many=True)
        return Response(serializer.data)


@action(detail=False, methods=['post'])
def recalculate(self, request):
    """Manually recalculate team stats for the current user"""
    stats = calculate_team_stats(request.user)
    serializer = self.get_serializer(stats)
    return Response(serializer.data)