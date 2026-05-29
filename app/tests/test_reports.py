from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TransactionSource, TransactionType
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.report_service import ReportService
from app.utils.dates import current_day_bounds


@pytest.mark.asyncio
async def test_today_report_groups_multiple_currencies(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=3001,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    start, _ = current_day_bounds(user.settings.timezone)
    repo = TransactionRepository(session)
    await repo.create(
        user_id=user.id,
        salary_period_id=None,
        type_=TransactionType.EXPENSE,
        amount=Decimal("25000"),
        currency="UZS",
        category_id=None,
        category_name="кафе",
        comment="кофе",
        operation_datetime=start,
        source=TransactionSource.TEXT,
    )
    await repo.create(
        user_id=user.id,
        salary_period_id=None,
        type_=TransactionType.EXPENSE,
        amount=Decimal("300"),
        currency="USD",
        category_id=None,
        category_name="аренда",
        comment="аренда",
        operation_datetime=start,
        source=TransactionSource.TEXT,
    )

    report = await ReportService(session).today(user)

    assert report.expenses["UZS"] == Decimal("25000.00")
    assert report.expenses["USD"] == Decimal("300.00")


@pytest.mark.asyncio
async def test_report_history_escapes_user_text(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=3002,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    await TransactionRepository(session).create(
        user_id=user.id,
        salary_period_id=None,
        type_=TransactionType.EXPENSE,
        amount=Decimal("1000"),
        currency="UZS",
        category_id=None,
        category_name=None,
        comment="<b>bad</b>",
        operation_datetime=current_day_bounds(user.settings.timezone)[0],
        source=TransactionSource.TEXT,
    )

    history = await ReportService(session).history(user)
    rendered = ReportService(session).render_history(history, user.settings.timezone)

    assert "&lt;b&gt;bad&lt;/b&gt;" in rendered
    assert "<b>bad</b>" not in rendered
