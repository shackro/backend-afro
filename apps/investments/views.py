from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from .models import Investment, InvestmentTransaction
from .serializers import (
    InvestmentSerializer, CreateInvestmentSerializer,
    InvestmentTransactionSerializer
)
from apps.products.models import Product
from apps.team.utils import process_team_commissions
from apps.transactions.models import Transaction as WalletTransaction


class InvestmentViewSet(viewsets.ModelViewSet):
    serializer_class = InvestmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['product__name']
    ordering_fields = ['created_at', 'amount', 'start_date', 'end_date']

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)

    @db_transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = CreateInvestmentSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data['product']
        amount = serializer.validated_data['amount']

        # Check if user has sufficient balance
        if request.user.balance < amount:
            return Response(
                {
                    'error': 'Insufficient balance',
                    'available_balance': float(request.user.balance),
                    'required_amount': float(amount),
                    'shortfall': float(amount - request.user.balance)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate daily income based on investment amount
        ratio = amount / product.price
        daily_income = product.daily_income * ratio

        # Create investment
        investment = Investment.objects.create(
            user=request.user,
            product=product,
            amount=amount,
            daily_income=daily_income,
            status='active',
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=product.validity_period)
        )

        # Deduct from user balance
        request.user.balance -= amount
        request.user.total_invested += amount
        request.user.save()

        # Create investment transaction record
        InvestmentTransaction.objects.create(
            investment=investment,
            user=request.user,
            transaction_type='investment',
            amount=amount,
            status='completed',
            reference=f"INV-{investment.id}",
            description=f"Investment in {product.name}"
        )

        # Create wallet transaction record for tracking
        WalletTransaction.objects.create(
            user=request.user,
            transaction_type='withdrawal',  # Money leaving wallet
            amount=amount,
            currency='USD',
            status='completed',
            payment_method='wallet',
            reference=f"INV-WLT-{investment.id}",
            description=f"Investment in {product.name}",
            completed_at=timezone.now()
        )

        # Process team commissions
        try:
            process_team_commissions(request.user, investment)
        except Exception as e:
            # Log error but don't fail the investment
            print(f"Commission processing error: {e}")

        return Response(
            InvestmentSerializer(investment).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        investment = self.get_object()

        if investment.status != 'active':
            return Response(
                {'error': 'Only active investments can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with db_transaction.atomic():
            investment.status = 'cancelled'
            investment.save()

            # Refund amount (minus any earnings)
            refund_amount = investment.amount - investment.total_paid
            if refund_amount > 0:
                request.user.balance += refund_amount
                request.user.total_invested -= investment.amount
                request.user.save()

                # Create refund transaction record
                WalletTransaction.objects.create(
                    user=request.user,
                    transaction_type='deposit',
                    amount=refund_amount,
                    currency='USD',
                    status='completed',
                    payment_method='wallet',
                    reference=f"REF-{investment.id}",
                    description=f"Refund for cancelled investment {investment.product.name}",
                    completed_at=timezone.now()
                )

        return Response({'status': 'investment cancelled'})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        investments = self.get_queryset()

        total_invested = investments.aggregate(total=Sum('amount'))['total'] or 0
        active_investments = investments.filter(status='active')
        active_count = active_investments.count()
        active_total = active_investments.aggregate(total=Sum('amount'))['total'] or 0

        total_earned = investments.aggregate(total=Sum('total_paid'))['total'] or 0
        expected_returns = active_investments.aggregate(
            total=Sum('total_expected_return')
        )['total'] or 0

        return Response({
            'total_investments': investments.count(),
            'total_invested': total_invested,
            'active_investments': active_count,
            'active_amount': active_total,
            'total_earned': total_earned,
            'expected_returns': expected_returns,
            'projected_profit': expected_returns - active_total
        })

    @action(detail=False, methods=['get'])
    def can_invest(self, request):
        """Check if user can invest a given amount"""
        amount = request.query_params.get('amount')
        if not amount:
            return Response({'error': 'Amount required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'can_invest': request.user.balance >= amount,
            'available_balance': float(request.user.balance),
            'required_amount': amount,
            'shortfall': max(0, amount - float(request.user.balance)) if request.user.balance < amount else 0
        })