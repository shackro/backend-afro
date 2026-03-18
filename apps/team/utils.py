# backend/apps/team/utils.py
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum, Q
from .models import TeamCommission, TeamStats, TeamTree
from apps.accounts.models import User


def process_team_commissions(investor, investment):
    """
    Process team commissions for an investment
    """
    print(f"\n🔍 Processing commissions for investor: {investor.email}")
    print(f"💰 Investment amount: ${investment.amount}")

    # Check if investor has any ancestors
    ancestors = TeamTree.objects.filter(
        user=investor,
        depth__lte=3
    ).select_related('ancestor').order_by('depth')

    ancestor_count = ancestors.count()
    print(f"📊 Found {ancestor_count} ancestors for {investor.email}")

    if ancestor_count == 0:
        print("❌ No ancestors found - no commissions to process")
        return

    commission_config = {
        1: {'level': 'B', 'percentage': Decimal('10.00')},
        2: {'level': 'C', 'percentage': Decimal('6.00')},
        3: {'level': 'D', 'percentage': Decimal('3.00')},
    }

    with transaction.atomic():
        commissions_created = 0

        for ancestor in ancestors:
            upline_user = ancestor.ancestor
            depth = ancestor.depth

            if depth not in commission_config:
                continue

            config = commission_config[depth]
            level_code = config['level']
            percentage = config['percentage']

            commission_amount = (investment.amount * percentage) / Decimal('100')

            print(
                f"  ➡️ Creating commission: {upline_user.email} gets {percentage}% (${commission_amount}) from {investor.email} (depth {depth})")

            # Create commission record
            commission = TeamCommission.objects.create(
                user=upline_user,
                from_user=investor,
                investment=investment,
                level=level_code,
                amount=commission_amount,
                percentage=percentage,
                status='pending'
            )

            # Update team stats
            stats, created = TeamStats.objects.get_or_create(user=upline_user)
            stats.pending_commission += commission_amount
            stats.total_commission_earned += commission_amount

            if depth == 1:
                stats.level_1_commission += commission_amount
            elif depth == 2:
                stats.level_2_commission += commission_amount
            elif depth == 3:
                stats.level_3_commission += commission_amount

            # Update volume metrics
            if depth == 1:
                stats.level_1_volume += investment.amount
            elif depth == 2:
                stats.level_2_volume += investment.amount
            elif depth == 3:
                stats.level_3_volume += investment.amount

            stats.team_volume += investment.amount
            stats.save()
            commissions_created += 1

        print(f"✅ Created {commissions_created} commission records")


def update_team_tree(user, referrer):
    """
    Update the team tree when a new user registers with a referral
    """
    if not referrer:
        return

    print(f"\n🔧 Updating team tree for {user.email} referred by {referrer.email}")

    with transaction.atomic():
        # Create direct referral relationship (Level 1)
        TeamTree.objects.create(
            user=user,
            ancestor=referrer,
            depth=1
        )
        print(f"  ✅ Created direct referral: {user.email} under {referrer.email} (depth 1)")

        # Update referrer's TeamStats level_1_count
        stats, created = TeamStats.objects.get_or_create(user=referrer)
        stats.level_1_count += 1
        stats.total_referrals += 1
        stats.save()

        # Create indirect relationships for Level 2 and Level 3
        referrer_ancestors = TeamTree.objects.filter(
            user=referrer,
            depth__lte=2
        ).select_related('ancestor')

        for ancestor in referrer_ancestors:
            new_depth = ancestor.depth + 1
            if new_depth <= 3:
                TeamTree.objects.create(
                    user=user,
                    ancestor=ancestor.ancestor,
                    depth=new_depth
                )
                print(
                    f"  ✅ Created indirect referral: {user.email} under {ancestor.ancestor.email} (depth {new_depth})")

                # Update ancestor's TeamStats
                ancestor_stats, created = TeamStats.objects.get_or_create(user=ancestor.ancestor)
                if new_depth == 2:
                    ancestor_stats.level_2_count += 1
                elif new_depth == 3:
                    ancestor_stats.level_3_count += 1
                ancestor_stats.save()


def calculate_team_stats(user):
    """
    Calculate and update team statistics for a user
    """
    from apps.investments.models import Investment
    from apps.accounts.models import User

    print(f"\n📊 Calculating team stats for {user.email}")

    # Get all descendants (team members) up to 3 levels deep
    descendants = TeamTree.objects.filter(
        ancestor=user,
        depth__lte=3
    ).select_related('user')

    # Calculate metrics by level
    level_counts = {1: 0, 2: 0, 3: 0}
    level_volumes = {1: 0, 2: 0, 3: 0}

    for descendant in descendants:
        level = descendant.depth
        level_counts[level] += 1

        # Calculate investments for this team member
        user_investments = Investment.objects.filter(
            user=descendant.user,
            status='active'
        ).aggregate(total=Sum('amount'))['total'] or 0
        level_volumes[level] += user_investments

    # Calculate total team volume (all levels)
    team_volume = Investment.objects.filter(
        user__in=descendants.values('user'),
        status='active'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Calculate personal volume
    personal_volume = Investment.objects.filter(
        user=user,
        status='active'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Get commission data from TeamCommission
    commissions = TeamCommission.objects.filter(user=user)

    pending_commissions = commissions.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
    paid_commissions = commissions.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
    total_commissions = pending_commissions + paid_commissions

    level_1_commission = commissions.filter(level='B').aggregate(total=Sum('amount'))['total'] or 0
    level_2_commission = commissions.filter(level='C').aggregate(total=Sum('amount'))['total'] or 0
    level_3_commission = commissions.filter(level='D').aggregate(total=Sum('amount'))['total'] or 0

    # Get bonus data from User model
    total_bonus = user.total_bonus_earned or 0
    bonus_count = user.bonus_count or 0

    # Update or create stats
    stats, created = TeamStats.objects.get_or_create(user=user)

    # Update counts
    stats.total_referrals = level_counts[1]
    stats.level_1_count = level_counts[1]
    stats.level_2_count = level_counts[2]
    stats.level_3_count = level_counts[3]

    stats.active_referrals = descendants.filter(
        user__investments__status='active'
    ).distinct().count()

    # Update volumes
    stats.level_1_volume = level_volumes[1]
    stats.level_2_volume = level_volumes[2]
    stats.level_3_volume = level_volumes[3]
    stats.team_volume = team_volume
    stats.personal_volume = personal_volume

    # Update commissions
    stats.pending_commission = pending_commissions
    stats.total_commission_earned = total_commissions
    stats.level_1_commission = level_1_commission
    stats.level_2_commission = level_2_commission
    stats.level_3_commission = level_3_commission

    # Update bonus information
    stats.total_bonus_earned = total_bonus
    stats.bonus_count = bonus_count

    # Determine level based on performance
    if level_counts[1] >= 20 and level_volumes[1] >= 100000:
        stats.current_level = 'D'
    elif level_counts[1] >= 10 and level_volumes[1] >= 50000:
        stats.current_level = 'C'
    else:
        stats.current_level = 'B'

    stats.save()
    print(f"✅ Updated stats for {user.email}")
    print(f"   Level 1 commission: ${stats.level_1_commission}")
    print(f"   Sign-up bonuses: ${stats.total_bonus_earned} ({stats.bonus_count} referrals)")

    return stats