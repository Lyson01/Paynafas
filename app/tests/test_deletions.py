from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import DeleteType, TransactionSource, TransactionType
from app.repositories.salary_period_repository import SalaryPeriodRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.delete_service import DeleteService
from app.services.export_service import ExportService
from app.services.report_service import ReportService
from app.services.subscription_service import SubscriptionService
from app.utils.dates import current_day_bounds, now_in_timezone, utc_now


@pytest.mark.asyncio
async def test_delete_single_transaction(session: AsyncSession) -> None:
    user = await _user(session, 9101)
    transaction = await _expense(session, user, "кофе")

    batch = await DeleteService(session).delete_single(user.id, transaction.id)

    assert batch is not None
    assert transaction.is_deleted is True
    assert batch.transactions_count == 1


@pytest.mark.asyncio
async def test_cannot_delete_another_users_transaction(session: AsyncSession) -> None:
    owner = await _user(session, 9102)
    attacker = await _user(session, 9103)
    transaction = await _expense(session, owner, "такси")

    batch = await DeleteService(session).delete_single(attacker.id, transaction.id)

    assert batch is None
    assert transaction.is_deleted is False


@pytest.mark.asyncio
async def test_deleted_transaction_does_not_affect_reports_and_balance(
    session: AsyncSession,
) -> None:
    user = await _user(session, 9104)
    now = utc_now()
    period = await SalaryPeriodRepository(session).create(
        user_id=user.id,
        salary_amount=Decimal("100000"),
        currency="UZS",
        start_datetime=now - timedelta(days=1),
        expected_next_salary_datetime=now + timedelta(days=30),
    )
    transaction = await _expense(session, user, "кофе", amount=Decimal("25000"))
    transaction.salary_period_id = period.id

    before = await ReportService(session).balance(user)
    await DeleteService(session).delete_single(user.id, transaction.id)
    after = await ReportService(session).balance(user)

    assert before[1] == Decimal("75000.00")
    assert after[1] == Decimal("100000.00")
    today = await ReportService(session).today(user)
    assert today.expenses == {}


@pytest.mark.asyncio
async def test_delete_today_week_month_period_and_all(session: AsyncSession) -> None:
    user = await _user(session, 9105)
    first = await _expense(session, user, "сегодня")
    await _expense(session, user, "неделя")
    await _expense(session, user, "месяц")

    today_batch = await DeleteService(session).delete_by_type(user, DeleteType.TODAY)
    assert today_batch is not None
    assert today_batch.transactions_count == 3

    await DeleteService(session).undo_last(user.id, today_batch.id)
    week_batch = await DeleteService(session).delete_by_type(user, DeleteType.WEEK)
    assert week_batch is not None
    assert week_batch.transactions_count == 3

    await DeleteService(session).undo_last(user.id, week_batch.id)
    month_batch = await DeleteService(session).delete_by_type(user, DeleteType.MONTH)
    assert month_batch is not None
    assert month_batch.transactions_count == 3

    await DeleteService(session).undo_last(user.id, month_batch.id)
    period = await SalaryPeriodRepository(session).create(
        user_id=user.id,
        salary_amount=Decimal("100000"),
        currency="UZS",
        start_datetime=utc_now() - timedelta(days=1),
        expected_next_salary_datetime=None,
    )
    first.salary_period_id = period.id
    period_batch = await DeleteService(session).delete_by_type(user, DeleteType.PERIOD)
    assert period_batch is not None
    assert period_batch.transactions_count == 1

    await DeleteService(session).undo_last(user.id, period_batch.id)
    all_batch = await DeleteService(session).delete_by_type(user, DeleteType.ALL)
    assert all_batch is not None
    assert all_batch.transactions_count == 3


@pytest.mark.asyncio
async def test_mass_delete_creates_batch_and_undo_restores(session: AsyncSession) -> None:
    user = await _user(session, 9106)
    first = await _expense(session, user, "кофе")
    second = await _expense(session, user, "такси")

    batch = await DeleteService(session).delete_selected(user.id, [first.id, second.id])
    restored = await DeleteService(session).undo_last(user.id, batch.id if batch else None)

    assert batch is not None
    assert restored is not None
    assert first.is_deleted is False
    assert second.is_deleted is False


@pytest.mark.asyncio
async def test_undo_delete_only_current_user_and_not_after_expiry(
    session: AsyncSession,
) -> None:
    owner = await _user(session, 9107)
    other = await _user(session, 9108)
    transaction = await _expense(session, owner, "кофе")
    batch = await DeleteService(session).delete_single(owner.id, transaction.id)
    assert batch is not None

    assert await DeleteService(session).undo_last(other.id, batch.id) is None
    assert transaction.is_deleted is True

    batch.expires_at = utc_now() - timedelta(seconds=1)
    assert await DeleteService(session).undo_last(owner.id, batch.id) is None
    assert transaction.is_deleted is True


@pytest.mark.asyncio
async def test_history_export_and_free_limit_ignore_deleted(
    session: AsyncSession,
) -> None:
    user = await _user(session, 9109)
    deleted = await _expense(session, user, "кофе")
    active = await _expense(session, user, "такси")
    await DeleteService(session).delete_single(user.id, deleted.id)

    history = await ReportService(session).history(user)
    csv_content, _ = await ExportService(session).csv_file(user, "alltime")

    assert [item.id for item in history] == [active.id]
    assert "кофе".encode() not in csv_content
    assert "такси".encode() in csv_content

    repo = TransactionRepository(session)
    for index in range(settings.free_monthly_transaction_limit - 1):
        await repo.create(
            user_id=user.id,
            salary_period_id=None,
            type_=TransactionType.EXPENSE,
            amount=Decimal(index + 1),
            currency="UZS",
            category_id=None,
            category_name="другое",
            comment="limit",
            operation_datetime=now_in_timezone(user.settings.timezone),
            source=TransactionSource.TEXT,
        )
    assert (await SubscriptionService(session).can_add_transaction(user))[0] is False
    await DeleteService(session).delete_single(user.id, active.id)
    assert (await SubscriptionService(session).can_add_transaction(user))[0] is True


async def _user(session: AsyncSession, telegram_id: int):
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=telegram_id,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    return user


async def _expense(
    session: AsyncSession,
    user,
    comment: str,
    amount: Decimal = Decimal("1000"),
):
    start, _ = current_day_bounds(user.settings.timezone)
    return await TransactionRepository(session).create(
        user_id=user.id,
        salary_period_id=None,
        type_=TransactionType.EXPENSE,
        amount=amount,
        currency="UZS",
        category_id=None,
        category_name="кафе",
        comment=comment,
        operation_datetime=start,
        source=TransactionSource.TEXT,
    )
