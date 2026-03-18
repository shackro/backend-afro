from django.shortcuts import get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from .models import Transaction


@staff_member_required
def approve_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)

    if transaction.status != 'pending':
        messages.error(request, f'Transaction {transaction.reference} is not pending.')
        return redirect('admin:transactions_transaction_changelist')

    # Process the transaction
    transaction.status = 'completed'
    transaction.completed_at = timezone.now()
    transaction.save()

    # Update user balance for deposits
    if transaction.transaction_type == 'deposit':
        user = transaction.user
        user.balance += transaction.amount
        user.save()
        messages.success(request, f'Deposit of {transaction.amount} {transaction.currency} approved for {user.email}')
    else:
        messages.success(request, f'Withdrawal of {transaction.amount} {transaction.currency} approved')

    return redirect('admin:transactions_transaction_changelist')


@staff_member_required
def reject_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)

    if transaction.status != 'pending':
        messages.error(request, f'Transaction {transaction.reference} is not pending.')
        return redirect('admin:transactions_transaction_changelist')

    # Reject the transaction
    transaction.status = 'failed'
    transaction.completed_at = timezone.now()
    transaction.save()

    # Refund balance for withdrawals
    if transaction.transaction_type == 'withdrawal':
        user = transaction.user
        user.balance += transaction.amount
        user.save()
        messages.warning(request,
                         f'Withdrawal of {transaction.amount} {transaction.currency} rejected - balance refunded')
    else:
        messages.warning(request, f'Deposit of {transaction.amount} {transaction.currency} rejected')

    return redirect('admin:transactions_transaction_changelist')