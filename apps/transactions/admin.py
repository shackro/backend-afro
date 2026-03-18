from django.contrib import admin
from django.utils import timezone
from django.db import transaction as db_transaction
from .models import Transaction, PaymentMethod, WithdrawalRequest


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'user_email', 'transaction_type', 'amount',
        'currency', 'status', 'payment_method', 'requested_at'
    ]
    list_filter = ['status', 'transaction_type', 'payment_method', 'currency']
    search_fields = ['reference', 'user__email', 'user__username', 'bank_name', 'account_number']
    readonly_fields = ['reference', 'requested_at', 'processed_at', 'completed_at', 'provider_response']
    actions = ['approve_withdrawals', 'reject_withdrawals', 'mark_as_processing']
    list_per_page = 25
    date_hierarchy = 'requested_at'

    fieldsets = (
        ('Transaction Information', {
            'fields': ('reference', 'user', 'transaction_type', 'amount', 'currency', 'status')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'bank_name', 'account_number', 'account_name',
                       'swift_code', 'mpesa_phone', 'mpesa_receipt', 'crypto_address', 'crypto_tx_hash')
        }),
        ('Provider Information', {
            'fields': ('provider_reference', 'provider_response'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'processed_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',)
        }),
    )

    def get_queryset(self, request):
        """Only show withdrawals in admin (deposits are auto-approved)"""
        qs = super().get_queryset(request)
        return qs.filter(transaction_type='withdrawal')

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'

    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly based on object state"""
        readonly = list(self.readonly_fields)

        if obj:  # Editing existing object
            # These fields should never be changed
            readonly.extend(['user', 'transaction_type', 'amount', 'currency', 'reference'])

            # If transaction is not pending, make more fields readonly
            if obj.status != 'pending':
                readonly.extend(['payment_method', 'bank_name', 'account_number',
                                 'account_name', 'swift_code', 'mpesa_phone',
                                 'crypto_address', 'status'])

        return readonly

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of transactions"""
        return False

    def approve_withdrawals(self, request, queryset):
        """Approve selected pending withdrawals"""
        approved_count = 0
        with db_transaction.atomic():
            for transaction in queryset.filter(
                    status='pending',
                    transaction_type='withdrawal'
            ):
                transaction.status = 'completed'
                transaction.completed_at = timezone.now()
                transaction.save()
                approved_count += 1

        self.message_user(
            request,
            f"✅ Successfully approved {approved_count} withdrawal(s).",
            level='SUCCESS'
        )

    approve_withdrawals.short_description = "Approve selected pending withdrawals"

    def reject_withdrawals(self, request, queryset):
        """Reject selected pending withdrawals and refund balance"""
        rejected_count = 0
        with db_transaction.atomic():
            for transaction in queryset.filter(
                    status='pending',
                    transaction_type='withdrawal'
            ):
                transaction.status = 'failed'
                transaction.completed_at = timezone.now()
                transaction.save()

                # Refund balance to user
                user = transaction.user
                user.balance += transaction.amount
                user.save()

                rejected_count += 1

        self.message_user(
            request,
            f"❌ Rejected {rejected_count} withdrawal(s) - balances refunded.",
            level='WARNING'
        )

    reject_withdrawals.short_description = "Reject selected pending withdrawals"

    def mark_as_processing(self, request, queryset):
        """Mark selected pending withdrawals as processing"""
        updated = queryset.filter(
            status='pending',
            transaction_type='withdrawal'
        ).update(
            status='processing',
            processed_at=timezone.now()
        )
        self.message_user(
            request,
            f"⏳ {updated} withdrawal(s) marked as processing.",
            level='INFO'
        )

    mark_as_processing.short_description = "Mark as processing"


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'method_type', 'is_default', 'created_at']
    list_filter = ['method_type', 'is_default']
    search_fields = ['user__email', 'account_number', 'mpesa_phone']
    readonly_fields = ['created_at']

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'

    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly based on object state"""
        readonly = ['created_at']
        if obj:  # Editing existing object
            readonly.extend(['user', 'method_type'])
        return readonly


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ['transaction_reference', 'user_email', 'status', 'reviewed_at']
    list_filter = ['transaction__status']
    search_fields = ['transaction__reference']
    readonly_fields = ['transaction', 'user_notes', 'reviewed_at', 'reviewed_by']

    def transaction_reference(self, obj):
        return obj.transaction.reference

    transaction_reference.short_description = 'Transaction'

    def user_email(self, obj):
        return obj.transaction.user.email

    user_email.short_description = 'User'

    def status(self, obj):
        return obj.transaction.status

    status.short_description = 'Status'

    def has_add_permission(self, request):
        """Prevent manual addition of withdrawal requests"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of withdrawal requests"""
        return False