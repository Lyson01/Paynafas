from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Plan, Subscription, SubscriptionStatus, TransactionSource, TransactionType
from app.repositories.salary_period_repository import SalaryPeriodRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService
from app.utils.dates import now_in_timezone, utc_now


@pytest.mark.asyncio
async def test_free_plan_limit(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=1001,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    repo = TransactionRepository(session)
    now = utc_now()
    period = await SalaryPeriodRepository(session).create(
        user_id=user.id,
        salary_amount=10_000_000,
        currency="UZS",
        start_datetime=now - timedelta(days=1),
        expected_next_salary_datetime=None,
    )
    for index in range(settings.free_monthly_transaction_limit):
        await repo.create(
            user_id=user.id,
            salary_period_id=period.id,
            type_=TransactionType.EXPENSE,
            amount=1000 + index,
            currency="UZS",
            category_id=None,
            category_name="другое",
            comment="test",
            operation_datetime=now_in_timezone(user.settings.timezone),
            source=TransactionSource.TEXT,
        )
    await session.flush()

    allowed, limit = await SubscriptionService(session).can_add_transaction(user)

    assert allowed is False
    assert limit == settings.free_monthly_transaction_limit


@pytest.mark.asyncio
async def test_activate_premium_disables_limit(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=1002,
        username=None,
        first_name="B",
        last_name=None,
        language_code="ru",
    )

    service = SubscriptionService(session)
    await service.activate_premium(user, days=30)

    assert await service.is_premium(user) is True
    allowed, _ = await service.can_add_transaction(user)
    assert allowed is True


@pytest.mark.asyncio
async def test_expired_premium_with_naive_datetime_returns_to_free(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=1003,
        username=None,
        first_name="B",
        last_name=None,
        language_code="ru",
    )
    user.plan = Plan.PREMIUM
    user.premium_until = datetime.utcnow() - timedelta(days=1)

    service = SubscriptionService(session)
    await service.refresh_user_plan(user)

    assert user.plan == Plan.FREE
    assert user.premium_until is None


@pytest.mark.asyncio
async def test_lifetime_premium_id_is_persisted_in_database(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    telegram_id = 6048168849
    monkeypatch.setattr(settings, "lifetime_premium_telegram_ids", [telegram_id])
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=telegram_id,
        username=None,
        first_name="Owner",
        last_name=None,
        language_code="ru",
    )

    service = SubscriptionService(session)

    assert await service.is_premium(user) is True
    assert user.plan == Plan.PREMIUM
    assert user.premium_until is not None
    assert user.premium_until.year == 9999

    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    subscription = result.scalar_one_or_none()
    assert subscription is not None
    assert subscription.expires_at is not None
    assert subscription.expires_at.year == 9999

    with pytest.raises(ValueError):
        await service.revoke_premium(user)
