from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction as db_transaction
from django.utils import timezone
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
import uuid
from .models import Transaction, PaymentMethod
from .serializers import (
    TransactionSerializer, CreateDepositSerializer,
    CreateWithdrawalSerializer, PaymentMethodSerializer,
    TransactionSummarySerializer
)
from apps.accounts.models import User


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'status', 'payment_method']
    ordering_fields = ['requested_at', 'amount']

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def deposit(self, request):
        """Deposit - automatically approved, balance updates immediately"""
        serializer = CreateDepositSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Generate unique reference
        reference = f"DEP-{uuid.uuid4().hex[:8].upper()}"

        with db_transaction.atomic():
            # Create transaction as completed immediately
            transaction = Transaction.objects.create(
                user=request.user,
                transaction_type='deposit',
                amount=serializer.validated_data['amount'],
                currency=serializer.validated_data['currency'],
                payment_method=serializer.validated_data['payment_method'],
                reference=reference,
                status='completed',  # Auto-approved
                completed_at=timezone.now(),

                # Store payment details
                bank_name=serializer.validated_data.get('bank_name', ''),
                account_number=serializer.validated_data.get('account_number', ''),
                account_name=serializer.validated_data.get('account_name', ''),
                swift_code=serializer.validated_data.get('swift_code', ''),
                mpesa_phone=serializer.validated_data.get('mpesa_phone', ''),
                crypto_address=serializer.validated_data.get('crypto_address', ''),
            )

            # IMPORTANT: Update user balance immediately for deposits
            request.user.balance += serializer.validated_data['amount']
            request.user.save()

        return Response(
            TransactionSerializer(transaction).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        """Withdrawal - requires admin approval, balance deducted immediately"""
        serializer = CreateWithdrawalSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Generate unique reference
        reference = f"WTH-{uuid.uuid4().hex[:8].upper()}"

        with db_transaction.atomic():
            # IMPORTANT: Deduct from user balance immediately to prevent double spending
            request.user.balance -= serializer.validated_data['amount']
            request.user.save()

            transaction = Transaction.objects.create(
                user=request.user,
                transaction_type='withdrawal',
                amount=serializer.validated_data['amount'],
                currency=serializer.validated_data['currency'],
                payment_method=serializer.validated_data['payment_method'],
                reference=reference,
                status='pending',  # Requires admin approval

                # Store payment details
                bank_name=serializer.validated_data.get('bank_name', ''),
                account_number=serializer.validated_data.get('account_number', ''),
                account_name=serializer.validated_data.get('account_name', ''),
                swift_code=serializer.validated_data.get('swift_code', ''),
                mpesa_phone=serializer.validated_data.get('mpesa_phone', ''),
                crypto_address=serializer.validated_data.get('crypto_address', ''),
            )

        return Response(
            TransactionSerializer(transaction).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending transaction (only for withdrawals)"""
        transaction = self.get_object()

        if transaction.status != 'pending':
            return Response(
                {'error': 'Only pending transactions can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if transaction.transaction_type != 'withdrawal':
            return Response(
                {'error': 'Only withdrawals can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with db_transaction.atomic():
            transaction.status = 'cancelled'
            transaction.save()

            # Refund balance
            request.user.balance += transaction.amount
            request.user.save()

        return Response({'status': 'transaction cancelled'})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        transactions = self.get_queryset()

        total_deposits = transactions.filter(
            transaction_type='deposit',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_withdrawals = transactions.filter(
            transaction_type='withdrawal',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        pending_deposits = transactions.filter(
            transaction_type='deposit',
            status='pending'
        ).aggregate(total=Sum('amount'))['total'] or 0

        pending_withdrawals = transactions.filter(
            transaction_type='withdrawal',
            status='pending'
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Get counts
        total_deposits_count = transactions.filter(transaction_type='deposit').count()
        total_withdrawals_count = transactions.filter(transaction_type='withdrawal').count()
        pending_deposits_count = transactions.filter(transaction_type='deposit', status='pending').count()
        pending_withdrawals_count = transactions.filter(transaction_type='withdrawal', status='pending').count()

        recent = transactions.order_by('-requested_at')[:10]

        return Response({
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'pending_deposits': pending_deposits,
            'pending_withdrawals': pending_withdrawals,
            'total_deposits_count': total_deposits_count,
            'total_withdrawals_count': total_withdrawals_count,
            'pending_deposits_count': pending_deposits_count,
            'pending_withdrawals_count': pending_withdrawals_count,
            'recent_transactions': TransactionSerializer(recent, many=True).data
        })


class PaymentMethodViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        payment_method = self.get_object()

        # Unset default for all other methods
        PaymentMethod.objects.filter(user=request.user).update(is_default=False)

        payment_method.is_default = True
        payment_method.save()

        return Response({'status': 'default payment method updated'})