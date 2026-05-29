from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import TransactionSource, TransactionType
from app.repositories.no_spend_repository import NoSpendRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.parser_service import ParserService
from app.services.reminder_service import ReminderService
from app.services.transaction_service import TransactionService
from app.utils.dates import local_day_bounds


@pytest.mark.asyncio
async def test_send_reminder_when_no_expenses(
    session: AsyncSession, session_maker: async_sessionmaker[AsyncSession]
) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=4001,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    now = datetime(2026, 5, 9, 16, 30, tzinfo=UTC)

    assert (
        await ReminderService(session_maker).should_send_daily_reminder(session, user, now) is True
    )


@pytest.mark.asyncio
async def test_no_reminder_if_expense_exists(
    session: AsyncSession, session_maker: async_sessionmaker[AsyncSession]
) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=4002,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    start, _ = local_day_bounds(datetime(2026, 5, 9).date(), user.settings.timezone)
    await TransactionRepository(session).create(
        user_id=user.id,
        salary_period_id=None,
        type_=TransactionType.EXPENSE,
        amount=Decimal("1000"),
        currency="UZS",
        category_id=None,
        category_name="кафе",
        comment="кофе",
        operation_datetime=start,
        source=TransactionSource.TEXT,
    )
    now = datetime(2026, 5, 9, 16, 30, tzinfo=UTC)

    assert (
        await ReminderService(session_maker).should_send_daily_reminder(session, user, now) is False
    )


@pytest.mark.asyncio
async def test_expense_after_no_spend_removes_no_spend_day(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=4004,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    day = datetime(2026, 5, 9).date()
    no_spend = NoSpendRepository(session)
    await no_spend.create_or_get(user_id=user.id, day=day, timezone=user.settings.timezone)
    parsed = ParserService().parse(
        "кофе 25000",
        timezone=user.settings.timezone,
        now=datetime(2026, 5, 9, 10, 0, tzinfo=ZoneInfo(user.settings.timezone)),
    )

    await TransactionService(session).save_parsed(user, parsed)

    assert await no_spend.exists(user.id, day) is False


@pytest.mark.asyncio
async def test_no_reminder_if_no_spend_marked(
    session: AsyncSession, session_maker: async_sessionmaker[AsyncSession]
) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=4003,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    await NoSpendRepository(session).create_or_get(
        user_id=user.id,
        day=datetime(2026, 5, 9).date(),
        timezone=user.settings.timezone,
    )
    now = datetime(2026, 5, 9, 16, 30, tzinfo=UTC)

    assert (
        await ReminderService(session_maker).should_send_daily_reminder(session, user, now) is False
    )
