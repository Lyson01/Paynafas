from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BillingPeriod, Plan, Subscription, SubscriptionSource, SubscriptionStatus


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        plan: Plan,
        started_at: datetime,
        expires_at: datetime | None,
        source: SubscriptionSource,
        billing_period: BillingPeriod = BillingPeriod.MANUAL,
        payment_invoice_id: int | None = None,
    ) -> Subscription:
        subscription = Subscription(
            user_id=user_id,
            plan=plan,
            billing_period=billing_period,
            started_at=started_at,
            expires_at=expires_at,
            source=source,
            payment_invoice_id=payment_invoice_id,
            status=SubscriptionStatus.ACTIVE,
        )
        self.session.add(subscription)
        await self.session.flush()
        return subscription

    async def has_active_premium(self, user_id: int, now: datetime) -> bool:
        result = await self.session.execute(
            select(Subscription.id).where(
                Subscription.user_id == user_id,
                Subscription.plan == Plan.PREMIUM,
                Subscription.status == SubscriptionStatus.ACTIVE,
                or_(Subscription.expires_at.is_(None), Subscription.expires_at > now),
            )
        )
        return result.scalar_one_or_none() is not None

    async def expire_user_active(self, user_id: int) -> None:
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        for subscription in result.scalars():
            subscription.status = SubscriptionStatus.EXPIRED
        await self.session.flush()
