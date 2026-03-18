from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import TeamLevel, TeamCommission, TeamStats, TeamTree


class TeamTreeInline(admin.TabularInline):
    """Inline for Team Tree - shows team members under a user"""
    model = TeamTree
    fk_name = 'ancestor'  # This is correct - it points to the ancestor field
    extra = 0
    fields = ['user', 'depth', 'user_email', 'user_investments']
    readonly_fields = ['user', 'depth', 'user_email', 'user_investments']
    can_delete = False
    verbose_name = 'Team Member'
    verbose_name_plural = 'Team Members'

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = 'Email'

    def user_investments(self, obj):
        from apps.investments.models import Investment
        total = Investment.objects.filter(user=obj.user, status='active').aggregate(
            total=Sum('amount'))['total'] or 0
        count = Investment.objects.filter(user=obj.user).count()
        return format_html(
            '<span title="{} investments">${}</span>',
            count,
            round(total, 2)
        )

    user_investments.short_description = 'Invested'


@admin.register(TeamLevel)
class TeamLevelAdmin(admin.ModelAdmin):
    list_display = ['level_code', 'name', 'commission_percentage',
                    'min_referrals', 'min_team_volume', 'member_count']
    list_filter = ['level_code']
    search_fields = ['name', 'description']

    fieldsets = (
        ('Level Information', {
            'fields': ('level_code', 'name', 'commission_percentage')
        }),
        ('Requirements', {
            'fields': ('min_referrals', 'min_team_volume')
        }),
        ('Description', {
            'fields': ('description',)
        }),
    )

    def member_count(self, obj):
        count = TeamStats.objects.filter(current_level=obj.level_code).count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)

    member_count.short_description = 'Members at this level'


@admin.register(TeamCommission)
class TeamCommissionAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'user_email', 'from_user_email',
                    'level_colored', 'amount_display', 'percentage',
                    'status_colored', 'created_at_display']
    list_filter = ['level', 'status', 'created_at']
    search_fields = ['user__email', 'from_user__email', 'investment__id']
    readonly_fields = ['user', 'from_user', 'investment', 'amount',
                       'percentage', 'level', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    actions = ['mark_as_paid', 'mark_as_cancelled']

    fieldsets = (
        ('Commission Information', {
            'fields': ('user', 'from_user', 'investment', 'level')
        }),
        ('Financial', {
            'fields': ('amount', 'percentage', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'paid_date', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'from_user', 'investment'
        )

    def id_short(self, obj):
        return str(obj.id)[:8] + '...'

    id_short.short_description = 'ID'

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = 'Recipient'
    user_email.admin_order_field = 'user__email'

    def from_user_email(self, obj):
        return obj.from_user.email

    from_user_email.short_description = 'From'
    from_user_email.admin_order_field = 'from_user__email'

    def level_colored(self, obj):
        colors = {
            'B': 'green',
            'C': 'blue',
            'D': 'purple'
        }
        color = colors.get(obj.level, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">Level {}</span>',
            color,
            obj.level
        )

    level_colored.short_description = 'Level'

    def amount_display(self, obj):
        return format_html('<span style="font-weight: bold;">${}</span>', obj.amount)

    amount_display.short_description = 'Amount'

    def status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status.upper()
        )

    status_colored.short_description = 'Status'

    def created_at_display(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    created_at_display.short_description = 'Date'

    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='paid',
            paid_date=timezone.now()
        )
        self.message_user(request, f"{updated} commissions marked as paid.")

    mark_as_paid.short_description = "Mark as paid"

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f"{updated} commissions cancelled.")

    mark_as_cancelled.short_description = "Mark as cancelled"


@admin.register(TeamStats)
class TeamStatsAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'current_level_colored', 'total_referrals',
                    'level_counts', 'team_volume_display', 'total_commission_display',
                    'pending_commission_display', 'updated_at_display']
    list_filter = ['current_level', 'updated_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['user', 'team_breakdown', 'commission_breakdown',
                       'level_progress', 'updated_at']

    fieldsets = (
        ('User', {
            'fields': ('user', 'current_level_colored')
        }),
        ('Team Metrics', {
            'fields': ('total_referrals', 'active_referrals', 'team_breakdown')
        }),
        ('Volume Metrics', {
            'fields': ('personal_volume', 'team_volume', 'level_volumes')
        }),
        ('Commission Metrics', {
            'fields': ('total_commission_earned', 'pending_commission',
                       'commission_breakdown')
        }),
        ('Level Progress', {
            'fields': ('level_progress',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'

    def current_level_colored(self, obj):
        colors = {
            'B': 'green',
            'C': 'blue',
            'D': 'purple'
        }
        color = colors.get(obj.current_level, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">Level {}</span>',
            color,
            obj.current_level
        )

    current_level_colored.short_description = 'Current Level'

    def level_counts(self, obj):
        return format_html(
            'L1: {} | L2: {} | L3: {}',
            obj.level_1_count,
            obj.level_2_count,
            obj.level_3_count
        )

    level_counts.short_description = 'Team Size by Level'

    def team_volume_display(self, obj):
        return format_html(
            '<span style="font-weight: bold;">${}</span>',
            round(obj.team_volume, 2)
        )

    team_volume_display.short_description = 'Team Volume'

    def total_commission_display(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">${}</span>',
            round(obj.total_commission_earned, 2)
        )

    total_commission_display.short_description = 'Total Commission'

    def pending_commission_display(self, obj):
        return format_html(
            '<span style="color: orange; font-weight: bold;">${}</span>',
            round(obj.pending_commission, 2)
        )

    pending_commission_display.short_description = 'Pending'

    def updated_at_display(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d %H:%M")

    updated_at_display.short_description = 'Last Updated'

    def team_breakdown(self, obj):
        return format_html(
            '''
            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                <p><strong>Level 1:</strong> {} members | Volume: ${}</p>
                <p><strong>Level 2:</strong> {} members | Volume: ${}</p>
                <p><strong>Level 3:</strong> {} members | Volume: ${}</p>
                <p><strong>Total Team:</strong> {} members | Volume: ${}</p>
            </div>
            ''',
            obj.level_1_count,
            round(obj.level_1_volume, 2),
            obj.level_2_count,
            round(obj.level_2_volume, 2),
            obj.level_3_count,
            round(obj.level_3_volume, 2),
            obj.total_referrals,
            round(obj.team_volume, 2)
        )

    team_breakdown.short_description = 'Team Breakdown'

    def level_volumes(self, obj):
        return format_html(
            'L1: ${} | L2: ${} | L3: ${}',
            round(obj.level_1_volume, 2),
            round(obj.level_2_volume, 2),
            round(obj.level_3_volume, 2)
        )

    level_volumes.short_description = 'Volume by Level'

    def commission_breakdown(self, obj):
        return format_html(
            '''
            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                <p><strong>Level 1 (10%):</strong> ${}</p>
                <p><strong>Level 2 (6%):</strong> ${}</p>
                <p><strong>Level 3 (3%):</strong> ${}</p>
                <p><strong>Total Earned:</strong> ${}</p>
                <p><strong>Pending:</strong> ${}</p>
            </div>
            ''',
            round(obj.level_1_commission, 2),
            round(obj.level_2_commission, 2),
            round(obj.level_3_commission, 2),
            round(obj.total_commission_earned, 2),
            round(obj.pending_commission, 2)
        )

    commission_breakdown.short_description = 'Commission Breakdown'

    def level_progress(self, obj):
        if obj.current_level == 'B':
            next_level = 'C'
            req_referrals = 10
            req_volume = 50000
            progress_referrals = min(100, (obj.level_1_count / req_referrals) * 100)
            progress_volume = min(100, (obj.level_1_volume / req_volume) * 100)
            return format_html(
                '''
                <div style="margin: 10px 0;">
                    <p><strong>Next Level: {}</strong></p>
                    <div style="margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span>Referrals: {}/{} ({:.1f}%)</span>
                        </div>
                        <div style="width: 100%; background: #e9ecef; border-radius: 5px; height: 10px;">
                            <div style="width: {:.1f}%; background: #28a745; height: 10px; border-radius: 5px;"></div>
                        </div>
                    </div>
                    <div>
                        <div style="display: flex; justify-content: space-between;">
                            <span>Volume: ${}/{} ({:.1f}%)</span>
                        </div>
                        <div style="width: 100%; background: #e9ecef; border-radius: 5px; height: 10px;">
                            <div style="width: {:.1f}%; background: #007bff; height: 10px; border-radius: 5px;"></div>
                        </div>
                    </div>
                </div>
                ''',
                next_level,
                obj.level_1_count,
                req_referrals,
                progress_referrals,
                progress_referrals,
                round(obj.level_1_volume, 2),
                req_volume,
                progress_volume,
                progress_volume
            )
        elif obj.current_level == 'C':
            next_level = 'D'
            req_referrals = 20
            req_volume = 100000
            progress_referrals = min(100, (obj.level_1_count / req_referrals) * 100)
            progress_volume = min(100, (obj.level_1_volume / req_volume) * 100)
            return format_html(
                '''
                <div style="margin: 10px 0;">
                    <p><strong>Next Level: {}</strong></p>
                    <div style="margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span>Referrals: {}/{} ({:.1f}%)</span>
                        </div>
                        <div style="width: 100%; background: #e9ecef; border-radius: 5px; height: 10px;">
                            <div style="width: {:.1f}%; background: #28a745; height: 10px; border-radius: 5px;"></div>
                        </div>
                    </div>
                    <div>
                        <div style="display: flex; justify-content: space-between;">
                            <span>Volume: ${}/{} ({:.1f}%)</span>
                        </div>
                        <div style="width: 100%; background: #e9ecef; border-radius: 5px; height: 10px;">
                            <div style="width: {:.1f}%; background: #007bff; height: 10px; border-radius: 5px;"></div>
                        </div>
                    </div>
                </div>
                ''',
                next_level,
                obj.level_1_count,
                req_referrals,
                progress_referrals,
                progress_referrals,
                round(obj.level_1_volume, 2),
                req_volume,
                progress_volume,
                progress_volume
            )
        else:
            return format_html('<span style="color: green;">Maximum level reached!</span>')

    level_progress.short_description = 'Progress to Next Level'


@admin.register(TeamTree)
class TeamTreeAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'ancestor_email', 'depth_colored', 'created_at']
    list_filter = ['depth']
    search_fields = ['user__email', 'ancestor__email']
    readonly_fields = ['user', 'ancestor', 'depth', 'created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'ancestor')

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = 'Team Member'

    def ancestor_email(self, obj):
        return obj.ancestor.email

    ancestor_email.short_description = 'Upline'

    def depth_colored(self, obj):
        colors = {
            1: 'green',
            2: 'blue',
            3: 'purple'
        }
        color = colors.get(obj.depth, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">Level {}</span>',
            color,
            obj.depth
        )

    depth_colored.short_description = 'Depth'

    def created_at(self, obj):
        return obj.user.created_at.strftime("%Y-%m-%d")

    created_at.short_description = 'Joined'