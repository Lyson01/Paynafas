from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TransactionSource, TransactionType
from app.repositories.salary_period_repository import SalaryPeriodRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.report_service import ReportService
from app.services.salary_period_service import SalaryPeriodService
from app.utils.dates import now_in_timezone


@pytest.mark.asyncio
async def test_salary_period_balance(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=2001,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    now = now_in_timezone(user.settings.timezone)
    period = await SalaryPeriodRepository(session).create(
        user_id=user.id,
        salary_amount=Decimal("5000000"),
        currency="UZS",
        start_datetime=now,
        expected_next_salary_datetime=None,
    )
    await TransactionRepository(session).create(
        user_id=user.id,
        salary_period_id=period.id,
        type_=TransactionType.EXPENSE,
        amount=Decimal("25000"),
        currency="UZS",
        category_id=None,
        category_name="кафе",
        comment="кофе",
        operation_datetime=now,
        source=TransactionSource.TEXT,
    )

    active, balance = await ReportService(session).balance(user)

    assert active.id == period.id
    assert balance == Decimal("4975000.00")


@pytest.mark.asyncio
async def test_salary_period_report_uses_operation_datetime(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=2002,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    now = now_in_timezone(user.settings.timezone)
    period = await SalaryPeriodRepository(session).create(
        user_id=user.id,
        salary_amount=Decimal("1000000"),
        currency="UZS",
        start_datetime=now,
        expected_next_salary_datetime=None,
    )
    await TransactionRepository(session).create(
        user_id=user.id,
        salary_period_id=period.id,
        type_=TransactionType.EXPENSE,
        amount=Decimal("100000"),
        currency="UZS",
        category_id=None,
        category_name="транспорт",
        comment="такси",
        operation_datetime=now,
        source=TransactionSource.TEXT,
    )

    _, data = await ReportService(session).salary_period(user)

    assert data is not None
    assert data.expenses["UZS"] == Decimal("100000.00")


@pytest.mark.asyncio
async def test_new_salary_period_closes_previous_active_period(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=2003,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    now = now_in_timezone(user.settings.timezone)
    repo = TransactionRepository(session)
    first_income = await repo.create(
        user_id=user.id,
        salary_period_id=None,
        type_=TransactionType.INCOME,
        amount=Decimal("1000000"),
        currency="UZS",
        category_id=None,
        category_name="зарплата",
        comment="зарплата",
        operation_datetime=now,
        source=TransactionSource.TEXT,
    )
    service = SalaryPeriodService(session)
    first_period = await service.create_from_income(first_income)
    second_datetime = now.replace(day=now.day + 1)
    second_income = await repo.create(
        user_id=user.id,
        salary_period_id=first_period.id,
        type_=TransactionType.INCOME,
        amount=Decimal("2000000"),
        currency="UZS",
        category_id=None,
        category_name="зарплата",
        comment="зарплата",
        operation_datetime=second_datetime,
        source=TransactionSource.TEXT,
    )

    second_period = await service.create_from_income(second_income)

    assert first_period.status.value == "closed"
    assert first_period.actual_next_salary_datetime == second_datetime
    assert second_period.status.value == "active"
    assert second_income.salary_period_id == second_period.id


@pytest.mark.asyncio
async def test_new_salary_period_closes_all_existing_active_periods(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=2004,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    now = now_in_timezone(user.settings.timezone)
    repo = SalaryPeriodRepository(session)
    first = await repo.create(
        user_id=user.id,
        salary_amount=Decimal("1000000"),
        currency="UZS",
        start_datetime=now,
        expected_next_salary_datetime=None,
    )
    second = await repo.create(
        user_id=user.id,
        salary_amount=Decimal("2000000"),
        currency="UZS",
        start_datetime=now.replace(day=now.day + 1),
        expected_next_salary_datetime=None,
    )

    await repo.close_active(user.id, now.replace(day=now.day + 2))

    assert first.status.value == "closed"
    assert second.status.value == "closed"
