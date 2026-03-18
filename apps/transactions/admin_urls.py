from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction as db_transaction
from .models import Transaction


@staff_member_required
def approve_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)

    if transaction.status != 'pending':
        messages.error(request, f'Transaction {transaction.reference} is not pending.')
        return redirect('admin:transactions_transaction_changelist')

    with db_transaction.atomic():
        transaction.status = 'completed'
        transaction.completed_at = timezone.now()
        transaction.save()

        # Update user balance for deposits
        if transaction.transaction_type == 'deposit':
            user = transaction.user
            user.balance += transaction.amount
            user.save()
            messages.success(
                request,
                f'✅ Deposit of {transaction.amount} {transaction.currency} approved for {user.email}'
            )
        else:
            messages.success(
                request,
                f'✅ Withdrawal of {transaction.amount} {transaction.currency} approved'
            )

    return redirect('admin:transactions_transaction_changelist')


@staff_member_required
def reject_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)

    if transaction.status != 'pending':
        messages.error(request, f'Transaction {transaction.reference} is not pending.')
        return redirect('admin:transactions_transaction_changelist')

    with db_transaction.atomic():
        transaction.status = 'failed'
        transaction.completed_at = timezone.now()
        transaction.save()

        # Refund balance for withdrawals
        if transaction.transaction_type == 'withdrawal':
            user = transaction.user
            user.balance += transaction.amount
            user.save()
            messages.warning(
                request,
                f'⚠️ Withdrawal of {transaction.amount} {transaction.currency} rejected - balance refunded to {user.email}'
            )
        else:
            messages.warning(
                request,
                f'⚠️ Deposit of {transaction.amount} {transaction.currency} rejected'
            )

    return redirect('admin:transactions_transaction_changelist')


# URL patterns for admin actions
urlpatterns = [
    path('approve/<uuid:transaction_id>/', approve_transaction, name='approve-transaction'),
    path('reject/<uuid:transaction_id>/', reject_transaction, name='reject-transaction'),
]