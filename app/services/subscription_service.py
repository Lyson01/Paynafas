from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import BillingPeriod, Plan, SubscriptionSource, User
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.utils.dates import current_month_bounds, utc_now

LIFETIME_PREMIUM_UNTIL = datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC)


class SubscriptionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.subscriptions = SubscriptionRepository(session)
        self.transactions = TransactionRepository(session)

    async def refresh_user_plan(self, user: User) -> None:
        if await self.ensure_lifetime_premium(user):
            return
        now = utc_now()
        premium_until = self._aware_datetime(user.premium_until)
        if user.plan == Plan.PREMIUM and premium_until and premium_until <= now:
            user.plan = Plan.FREE
            user.premium_until = None
            await self.subscriptions.expire_user_active(user.id)
            await self.session.flush()

    async def is_premium(self, user: User) -> bool:
        await self.refresh_user_plan(user)
        premium_until = self._aware_datetime(user.premium_until)
        if user.plan != Plan.PREMIUM or premium_until is None or premium_until <= utc_now():
            return False
        return await self.subscriptions.has_active_premium(user.id, utc_now())

    async def can_add_transaction(self, user: User) -> tuple[bool, int]:
        await self.refresh_user_plan(user)
        if await self.is_premium(user):
            return True, settings.free_monthly_transaction_limit
        start, end = current_month_bounds(user.settings.timezone)
        count = await self.transactions.count_for_month(user.id, start, end)
        return (
            count < settings.free_monthly_transaction_limit,
            settings.free_monthly_transaction_limit,
        )

    async def activate_premium(
        self,
        user: User,
        *,
        days: int = 30,
        source: SubscriptionSource = SubscriptionSource.ADMIN,
        billing_period: BillingPeriod = BillingPeriod.MANUAL,
        payment_invoice_id: int | None = None,
    ) -> None:
        if days <= 0:
            raise ValueError("Premium duration must be positive")
        now = utc_now()
        premium_until = self._aware_datetime(user.premium_until)
        base = premium_until if premium_until and premium_until > now else now
        user.plan = Plan.PREMIUM
        user.premium_until = base + timedelta(days=days)
        await self.subscriptions.create(
            user_id=user.id,
            plan=Plan.PREMIUM,
            started_at=now,
            expires_at=user.premium_until,
            source=source,
            billing_period=billing_period,
            payment_invoice_id=payment_invoice_id,
        )
        await self.session.flush()

    async def ensure_lifetime_premium(self, user: User) -> bool:
        if user.telegram_id not in settings.lifetime_premium_telegram_ids:
            return False

        user.plan = Plan.PREMIUM
        user.premium_until = LIFETIME_PREMIUM_UNTIL

        has_subscription = await self.subscriptions.has_active_premium(user.id, utc_now())
        if not has_subscription:
            await self.subscriptions.create(
                user_id=user.id,
                plan=Plan.PREMIUM,
                started_at=utc_now(),
                expires_at=LIFETIME_PREMIUM_UNTIL,
                source=SubscriptionSource.ADMIN,
                billing_period=BillingPeriod.MANUAL,
                payment_invoice_id=None,
            )
        await self.session.flush()
        return True

    async def revoke_premium(self, user: User) -> None:
        if user.telegram_id in settings.lifetime_premium_telegram_ids:
            raise ValueError("Cannot revoke configured lifetime premium user")
        user.plan = Plan.FREE
        user.premium_until = None
        await self.subscriptions.expire_user_active(user.id)
        await self.session.flush()

    def _aware_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
