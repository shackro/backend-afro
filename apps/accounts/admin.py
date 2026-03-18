from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fieldsets = (
        ('Personal Information', {
            'fields': ('profile_picture', 'date_of_birth', 'occupation')
        }),
        ('Address', {
            'fields': ('address', 'city', 'country', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Security', {
            'fields': ('two_factor_enabled', 'notification_preferences'),
            'classes': ('collapse',)
        }),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'first_name', 'last_name',
                    'phone_number', 'referral_code', 'referral_count_display',
                    'balance_display', 'is_kyc_verified', 'is_active',
                    'date_joined_display', 'action_buttons']
    list_filter = ['is_kyc_verified', 'is_active', 'is_staff',
                   'is_superuser', 'preferred_currency', 'created_at']
    search_fields = ['email', 'username', 'first_name', 'last_name',
                     'phone_number', 'referral_code']
    readonly_fields = ['id', 'referral_code', 'referral_link_display',
                       'referral_count_display', 'balance_display',
                       'total_invested_display', 'total_earned_display',
                       'total_withdrawn_display', 'available_balance_display',
                       'created_at', 'updated_at', 'last_login', 'date_joined']

    fieldsets = (
        ('Login Information', {
            'fields': ('email', 'username', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone_number')
        }),
        ('Referral Information', {
            'fields': ('referral_code', 'referred_by', 'referral_link_display',
                       'referral_count_display'),
            'classes': ('collapse',)
        }),
        ('Wallet Information', {
            'fields': ('balance_display', 'available_balance_display',
                       'total_invested_display', 'total_earned_display',
                       'total_withdrawn_display', 'preferred_currency'),
            'classes': ('collapse',)
        }),
        ('KYC Information', {
            'fields': ('is_kyc_verified', 'id_document', 'id_document_type'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('created_at', 'updated_at', 'last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    inlines = [UserProfileInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')

    def date_joined_display(self, obj):
        return obj.date_joined.strftime("%Y-%m-%d %H:%M")

    date_joined_display.short_description = "Joined"
    date_joined_display.admin_order_field = 'date_joined'

    def balance_display(self, obj):
        return format_html('<span style="color: #28a745; font-weight: bold;">${}</span>',
                           obj.balance)

    balance_display.short_description = "Balance"

    def available_balance_display(self, obj):
        return format_html('<span style="color: #17a2b8;">${}</span>',
                           obj.available_balance)

    available_balance_display.short_description = "Available"

    def total_invested_display(self, obj):
        return f"${obj.total_invested}"

    total_invested_display.short_description = "Total Invested"

    def total_earned_display(self, obj):
        return f"${obj.total_earned}"

    total_earned_display.short_description = "Total Earned"

    def total_withdrawn_display(self, obj):
        return f"${obj.total_withdrawn}"

    total_withdrawn_display.short_description = "Total Withdrawn"

    def referral_link_display(self, obj):
        if obj.referral_link:
            return format_html('<a href="{}" target="_blank">{}</a>',
                               obj.referral_link, obj.referral_link)
        return "-"

    referral_link_display.short_description = "Referral Link"

    def referral_count_display(self, obj):
        count = obj.referral_count
        url = reverse('admin:accounts_user_changelist') + f'?referred_by__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)

    referral_count_display.short_description = "Referrals"

    def action_buttons(self, obj):
        return format_html(
            '<a class="button" href="{}" style="background: #28a745; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; margin-right: 5px;">View Wallet</a>'
            '<a class="button" href="{}" style="background: #17a2b8; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">View Referrals</a>',
            reverse('admin:transactions_transaction_changelist') + f'?user__id__exact={obj.id}',
            reverse('admin:accounts_user_changelist') + f'?referred_by__id__exact={obj.id}'
        )

    action_buttons.short_description = 'Actions'
    action_buttons.allow_tags = True

    actions = ['verify_kyc', 'suspend_users', 'activate_users',
               'send_test_email', 'export_users_csv']

    def verify_kyc(self, request, queryset):
        updated = queryset.update(is_kyc_verified=True)
        self.message_user(request, f"{updated} users KYC verified.")

    verify_kyc.short_description = "Verify KYC for selected users"

    def suspend_users(self, request, queryset):
        updated = queryset.update(is_active=False, is_suspended=True)
        self.message_user(request, f"{updated} users suspended.")

    suspend_users.short_description = "Suspend selected users"

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True, is_suspended=False)
        self.message_user(request, f"{updated} users activated.")

    activate_users.short_description = "Activate selected users"

    def send_test_email(self, request, queryset):
        # Implement email sending logic
        self.message_user(request, f"Test email sent to {queryset.count()} users.")

    send_test_email.short_description = "Send test email"

    def export_users_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'

        writer = csv.writer(response)
        writer.writerow(['Email', 'Username', 'First Name', 'Last Name',
                         'Phone', 'Balance', 'Joined', 'KYC Verified'])

        for user in queryset:
            writer.writerow([
                user.email, user.username, user.first_name, user.last_name,
                user.phone_number, user.balance, user.date_joined, user.is_kyc_verified
            ])

        return response

    export_users_csv.short_description = "Export selected users to CSV"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'user_name', 'city', 'country',
                    'two_factor_enabled', 'profile_picture_preview']
    list_filter = ['two_factor_enabled', 'country', 'city']
    search_fields = ['user__email', 'user__first_name', 'user__last_name',
                     'city', 'country']
    readonly_fields = ['profile_picture_preview', 'notification_preferences']

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Profile Picture', {
            'fields': ('profile_picture', 'profile_picture_preview')
        }),
        ('Personal Details', {
            'fields': ('date_of_birth', 'occupation')
        }),
        ('Address', {
            'fields': ('address', 'city', 'country', 'postal_code')
        }),
        ('Security', {
            'fields': ('two_factor_enabled', 'notification_preferences')
        }),
    )

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    user_name.short_description = 'Name'
    user_name.admin_order_field = 'user__first_name'

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                               obj.profile_picture.url)
        return "No image"

    profile_picture_preview.short_description = 'Preview'