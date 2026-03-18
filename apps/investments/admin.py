from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db import transaction
from .models import Investment, InvestmentTransaction


class InvestmentTransactionInline(admin.TabularInline):
    """Inline for Investment Transactions"""
    model = InvestmentTransaction
    extra = 0
    readonly_fields = ['created_at', 'reference']
    fields = ['transaction_type', 'amount', 'status', 'reference', 'created_at']
    can_delete = False


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'product', 'amount', 'status', 'created_at']
    list_filter = ['status', 'product', 'created_at']
    search_fields = ['user__email', 'product__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [InvestmentTransactionInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Investment Information', {
            'fields': ('id', 'user', 'product', 'status')
        }),
        ('Financial Details', {
            'fields': ('amount', 'daily_income', 'total_expected_return', 'total_paid')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'last_payout_date', 'created_at', 'updated_at')
        }),
        ('Progress', {
            'fields': ('remaining_payouts',)
        }),
    )

    actions = ['mark_as_active', 'mark_as_completed', 'mark_as_cancelled']

    def mark_as_active(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='active',
            start_date=timezone.now()
        )
        self.message_user(request, f"{updated} investments marked as active.")

    mark_as_active.short_description = "Mark as active"

    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status='active').update(
            status='completed',
            end_date=timezone.now()
        )
        self.message_user(request, f"{updated} investments marked as completed.")

    mark_as_completed.short_description = "Mark as completed"

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f"{updated} investments cancelled.")

    mark_as_cancelled.short_description = "Mark as cancelled"


@admin.register(InvestmentTransaction)
class InvestmentTransactionAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user', 'investment', 'transaction_type', 'amount', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['reference', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Transaction Information', {
            'fields': ('reference', 'user', 'investment', 'transaction_type')
        }),
        ('Financial', {
            'fields': ('amount', 'status')
        }),
        ('Details', {
            'fields': ('description', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )