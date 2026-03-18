from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from apps.investments.models import Investment, InvestmentTransaction
from apps.transactions.models import Transaction as WalletTransaction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Process daily payouts for active investments'

    def handle(self, *args, **options):
        self.stdout.write('Starting daily payout processing...')

        # Get all active investments
        active_investments = Investment.objects.filter(
            status='active',
            end_date__gt=timezone.now()
        ).select_related('user', 'product')

        processed = 0
        errors = 0
        total_paid = 0

        for investment in active_investments:
            try:
                with transaction.atomic():
                    # Calculate today's payout
                    daily_payout = investment.daily_income

                    # Update investment
                    investment.total_paid += daily_payout
                    investment.remaining_payouts -= 1

                    # Check if investment is completed
                    if investment.remaining_payouts <= 0:
                        investment.status = 'completed'

                    investment.save()

                    # Add to user balance
                    user = investment.user
                    user.balance += daily_payout
                    user.total_earned += daily_payout
                    user.save()

                    # Create investment transaction record
                    InvestmentTransaction.objects.create(
                        investment=investment,
                        user=user,
                        transaction_type='daily_payout',
                        amount=daily_payout,
                        status='completed',
                        reference=f"PAY-{investment.id}-{timezone.now().strftime('%Y%m%d')}",
                        description=f"Daily payout for {investment.product.name}"
                    )

                    # Create wallet transaction record
                    WalletTransaction.objects.create(
                        user=user,
                        transaction_type='deposit',
                        amount=daily_payout,
                        currency='USD',
                        status='completed',
                        payment_method='investment_return',
                        reference=f"WLT-PAY-{investment.id}-{timezone.now().strftime('%Y%m%d')}",
                        description=f"Daily return from {investment.product.name}",
                        completed_at=timezone.now()
                    )

                    processed += 1
                    total_paid += daily_payout

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing investment {investment.id}: {e}')
                )
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Daily payout processing completed. '
                f'Processed: {processed}, Errors: {errors}, Total Paid: ${total_paid}'
            )
        )