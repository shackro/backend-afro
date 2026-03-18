# backend/apps/products/admin.py

from django.contrib import admin
from django.db import models
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'daily_income', 'validity_period',
                    'display_b_commission', 'display_c_commission',
                    'display_d_commission', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']

    # Make commission fields read-only and exclude them from the add form
    readonly_fields = ['display_b_commission', 'display_c_commission',
                       'display_d_commission', 'total_return_display',
                       'roi_percentage_display', 'daily_roi_percentage_display']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'image', 'is_active')
        }),
        ('Financial Details', {
            'fields': ('price', 'daily_income', 'validity_period')
        }),
        ('Auto-calculated Commissions', {
            'fields': ('display_b_commission', 'display_c_commission', 'display_d_commission'),
            'description': 'Commissions are automatically calculated as percentages of daily income: Level 1 (10%), Level 2 (6%), Level 3 (3%)'
        }),
        ('Investment Limits', {
            'fields': ('min_investment', 'max_investment'),
            'classes': ('collapse',)
        }),
        ('Calculated Returns', {
            'fields': ('total_return_display', 'roi_percentage_display', 'daily_roi_percentage_display'),
            'classes': ('collapse',)
        }),
    )

    def display_b_commission(self, obj):
        if obj.pk and obj.daily_income:  # Only show if object exists and has daily_income
            return f"${obj.b_commission:.2f} (10%)"
        return "Will be calculated after saving"

    display_b_commission.short_description = "Level 1 Commission"

    def display_c_commission(self, obj):
        if obj.pk and obj.daily_income:
            return f"${obj.c_commission:.2f} (6%)"
        return "Will be calculated after saving"

    display_c_commission.short_description = "Level 2 Commission"

    def display_d_commission(self, obj):
        if obj.pk and obj.daily_income:
            return f"${obj.d_commission:.2f} (3%)"
        return "Will be calculated after saving"

    display_d_commission.short_description = "Level 3 Commission"

    def total_return_display(self, obj):
        if obj.pk and obj.daily_income and obj.validity_period:
            return f"${obj.total_return:.2f}"
        return "Will be calculated after saving"

    total_return_display.short_description = "Total Return"

    def roi_percentage_display(self, obj):
        if obj.pk and obj.price and obj.price > 0:
            return f"{obj.roi_percentage:.1f}%"
        return "Will be calculated after saving"

    roi_percentage_display.short_description = "ROI Percentage"

    def daily_roi_percentage_display(self, obj):
        if obj.pk and obj.price and obj.price > 0:
            return f"{obj.daily_roi_percentage:.2f}%"
        return "Will be calculated after saving"

    daily_roi_percentage_display.short_description = "Daily ROI"

    # Override get_fieldsets to conditionally show calculated fields
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not obj:  # If this is an add form
            # Remove calculated fields from add form since they need existing object
            fieldsets = [
                ('Basic Information', {
                    'fields': ('name', 'description', 'image', 'is_active')
                }),
                ('Financial Details', {
                    'fields': ('price', 'daily_income', 'validity_period')
                }),
                ('Investment Limits', {
                    'fields': ('min_investment', 'max_investment'),
                    'classes': ('collapse',)
                }),
            ]
        return fieldsets