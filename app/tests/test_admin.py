from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaymentRequestStatus, Plan
from app.repositories.payment_repository import PaymentRepository
from app.repositories.user_repository import UserRepository
from app.services.admin_service import AdminService


@pytest.mark.asyncio
async def test_admin_approve_payment_activates_premium(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=7001,
        username=None,
        first_name="Pay",
        last_name=None,
        language_code="ru",
    )
    payment = await PaymentRepository(session).create(
        user_id=user.id,
        amount=Decimal("9900"),
        currency="UZS",
        receipt_file_id="file-id",
    )

    telegram_id = await AdminService(session).approve_payment(payment.id, days=30)

    assert telegram_id == user.telegram_id
    assert payment.status == PaymentRequestStatus.APPROVED
    assert user.plan == Plan.PREMIUM
    assert user.premium_until is not None


@pytest.mark.asyncio
async def test_admin_reject_payment_keeps_free_plan(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=7002,
        username=None,
        first_name="Pay",
        last_name=None,
        language_code="ru",
    )
    payment = await PaymentRepository(session).create(
        user_id=user.id,
        amount=Decimal("9900"),
        currency="UZS",
        receipt_file_id="file-id",
    )

    telegram_id = await AdminService(session).reject_payment(payment.id)

    assert telegram_id == user.telegram_id
    assert payment.status == PaymentRequestStatus.REJECTED
    assert user.plan == Plan.FREE


@pytest.mark.asyncio
async def test_admin_cannot_approve_payment_twice(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=7003,
        username=None,
        first_name="Pay",
        last_name=None,
        language_code="ru",
    )
    payment = await PaymentRepository(session).create(
        user_id=user.id,
        amount=Decimal("9900"),
        currency="UZS",
        receipt_file_id="file-id",
    )
    service = AdminService(session)

    assert await service.approve_payment(payment.id, days=30) == user.telegram_id
    first_until = user.premium_until

    assert await service.approve_payment(payment.id, days=30) is None
    assert user.premium_until == first_until
