from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.models import (
    PaymentInvoice,
    PaymentInvoiceStatus,
    PaymentMethod,
    PaymentPlan,
    PaymentProviderCode,
    Plan,
    Subscription,
    SubscriptionStatus,
)
from app.repositories.user_repository import UserRepository
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.utils.dates import utc_now


@pytest.mark.asyncio
async def test_create_monthly_and_yearly_invoices(session: AsyncSession) -> None:
    user = await _user(session, 9001)
    service = PaymentService(session)

    month = await service.create_invoice(user, PaymentPlan.PREMIUM_MONTH, PaymentMethod.UZCARD_HUMO)
    year = await service.create_invoice(
        user, PaymentPlan.PREMIUM_YEAR, PaymentMethod.VISA_MASTERCARD
    )

    assert month.amount == Decimal(settings.premium_monthly_price_uzs)
    assert month.currency == "UZS"
    assert year.amount == Decimal(settings.premium_yearly_price_uzs)
    assert year.status == PaymentInvoiceStatus.PENDING
    assert month.payment_url


@pytest.mark.asyncio
async def test_payment_methods_depend_on_country_and_availability(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    uz_user = await _user(session, 9002)
    service = PaymentService(session)

    assert {option.method for option in service.available_methods(uz_user)} == {
        PaymentMethod.VISA_MASTERCARD,
        PaymentMethod.UZCARD_HUMO,
    }

    non_uz_user = await _user(session, 9003)
    non_uz_user.settings.country_code = "US"
    non_uz_user.settings.default_currency = "USD"
    assert {option.method for option in service.available_methods(non_uz_user)} == {
        PaymentMethod.VISA_MASTERCARD
    }

    monkeypatch.setattr(settings, "international_payments_enabled", False)
    assert service.available_methods(non_uz_user) == []


@pytest.mark.asyncio
async def test_successful_payment_activates_premium(session: AsyncSession) -> None:
    user = await _user(session, 9004)
    service = PaymentService(session)
    invoice = await service.create_invoice(
        user, PaymentPlan.PREMIUM_MONTH, PaymentMethod.VISA_MASTERCARD
    )

    paid = await service.mock_mark_paid(invoice.id)

    assert paid is not None
    assert paid.status == PaymentInvoiceStatus.PAID
    assert user.plan == Plan.PREMIUM
    assert user.premium_until is not None
    assert await SubscriptionService(session).is_premium(user) is True


@pytest.mark.asyncio
async def test_webhook_idempotency_does_not_double_extend_subscription(
    session: AsyncSession,
) -> None:
    user = await _user(session, 9005)
    service = PaymentService(session)
    invoice = await service.create_invoice(
        user, PaymentPlan.PREMIUM_MONTH, PaymentMethod.VISA_MASTERCARD
    )
    payload = {"event_id": "evt-idem", "invoice_id": invoice.id, "status": "paid"}

    await service.process_webhook(PaymentProviderCode.MOCK, payload, {})
    first_until = user.premium_until
    await service.process_webhook(PaymentProviderCode.MOCK, payload, {})

    assert user.premium_until == first_until
    result = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_failed_and_expired_payment_do_not_activate_premium(session: AsyncSession) -> None:
    user = await _user(session, 9006)
    service = PaymentService(session)
    failed = await service.create_invoice(
        user, PaymentPlan.PREMIUM_MONTH, PaymentMethod.VISA_MASTERCARD
    )
    await service.apply_status(failed, PaymentInvoiceStatus.FAILED)

    expired = await service.create_invoice(
        user, PaymentPlan.PREMIUM_MONTH, PaymentMethod.VISA_MASTERCARD
    )
    expired.expires_at = utc_now() - timedelta(minutes=1)
    await service.check_invoice(user, expired.id)

    assert user.plan == Plan.FREE
    assert failed.status == PaymentInvoiceStatus.FAILED
    assert expired.status == PaymentInvoiceStatus.EXPIRED


@pytest.mark.asyncio
async def test_active_premium_extends_from_existing_until(session: AsyncSession) -> None:
    user = await _user(session, 9007)
    subscription = SubscriptionService(session)
    await subscription.activate_premium(user, days=30)
    first_until = user.premium_until
    assert first_until is not None

    invoice = await PaymentService(session).create_invoice(
        user, PaymentPlan.PREMIUM_MONTH, PaymentMethod.VISA_MASTERCARD
    )
    await PaymentService(session).mock_mark_paid(invoice.id)

    assert user.premium_until is not None
    assert user.premium_until > first_until + timedelta(days=29)


@pytest.mark.asyncio
async def test_premium_persists_after_reload_from_database(
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    async with session_maker() as session:
        user = await _user(session, 9008)
        invoice = await PaymentService(session).create_invoice(
            user, PaymentPlan.PREMIUM_MONTH, PaymentMethod.VISA_MASTERCARD
        )
        await PaymentService(session).mock_mark_paid(invoice.id)
        premium_until = user.premium_until
        await session.commit()

    async with session_maker() as restarted_session:
        reloaded = await UserRepository(restarted_session).get_by_telegram_id(9008)
        assert reloaded is not None
        assert reloaded.plan == Plan.PREMIUM
        assert reloaded.premium_until is not None
        assert premium_until is not None
        assert reloaded.premium_until.replace(tzinfo=None) == premium_until.replace(tzinfo=None)
        assert await SubscriptionService(restarted_session).is_premium(reloaded) is True

        invoices = await restarted_session.execute(
            select(PaymentInvoice).where(
                PaymentInvoice.user_id == reloaded.id,
                PaymentInvoice.status == PaymentInvoiceStatus.PAID,
            )
        )
        assert invoices.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_redis_flush_does_not_remove_premium(
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    redis_cache = {"premium": "temporary-cache-only"}
    async with session_maker() as session:
        user = await _user(session, 9009)
        await SubscriptionService(session).activate_premium(user, days=30)
        await session.commit()

    redis_cache.clear()

    async with session_maker() as session:
        reloaded = await UserRepository(session).get_by_telegram_id(9009)
        assert reloaded is not None
        assert redis_cache == {}
        assert await SubscriptionService(session).is_premium(reloaded) is True


@pytest.mark.asyncio
async def test_expired_premium_switches_user_to_free(session: AsyncSession) -> None:
    user = await _user(session, 9010)
    await SubscriptionService(session).activate_premium(user, days=30)
    user.premium_until = utc_now() - timedelta(seconds=1)

    assert await SubscriptionService(session).is_premium(user) is False
    assert user.plan == Plan.FREE

    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    assert result.scalar_one_or_none() is None


async def _user(session: AsyncSession, telegram_id: int):
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=telegram_id,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    return user
