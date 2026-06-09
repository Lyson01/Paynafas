from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import history_delete_keyboard
from app.handlers.common import get_user_from_callback, get_user_from_message
from app.locales import t
from app.repositories.no_spend_repository import NoSpendRepository
from app.services.report_service import ReportService
from app.services.subscription_service import SubscriptionService
from app.services.transaction_service import TransactionService
from app.utils.dates import current_day_bounds, now_in_timezone
from app.utils.money import format_money

router = Router(name="reports")


@router.message(Command("today"))
async def cmd_today(message: Message, session: AsyncSession) -> None:
    await _send_report(message, session, "today")


@router.message(Command("week"))
async def cmd_week(message: Message, session: AsyncSession) -> None:
    await _send_report(message, session, "week")


@router.message(Command("month"))
async def cmd_month(message: Message, session: AsyncSession) -> None:
    await _send_report(message, session, "month")


@router.message(Command("alltime"))
async def cmd_alltime(message: Message, session: AsyncSession) -> None:
    await _send_report(message, session, "alltime")


@router.message(Command("categories"))
async def cmd_categories(message: Message, session: AsyncSession) -> None:
    await _send_report(message, session, "month")


@router.message(Command("period"))
async def cmd_period(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    service = ReportService(session)
    period, data = await service.salary_period(user)
    if period is None or data is None:
        await message.answer(
            "Активного зарплатного периода пока нет. "
            "Добавь доход как зарплату, чтобы начать период."
        )
        return
    premium = await SubscriptionService(session).is_premium(user)
    await message.answer(
        service.render_period_report(period, data, user.settings.timezone, premium=premium)
    )


@router.message(Command("balance"))
async def cmd_balance(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    period, balance = await ReportService(session).balance(user)
    if period is None or balance is None:
        await message.answer("Активного зарплатного периода пока нет.")
        return
    await message.answer(f"Остаток от зарплаты: {format_money(balance, period.currency)}")


@router.message(Command("history"))
@router.message(F.text == "📜 История")
async def cmd_history(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    premium = await SubscriptionService(session).is_premium(user)
    limit = 50 if premium else 10
    history = await ReportService(session).history(user, limit)
    await message.answer(
        ReportService(session).render_history(history, user.settings.timezone),
        reply_markup=history_delete_keyboard([item.id for item in history]),
    )


@router.message(Command("no_spend_today"))
async def cmd_no_spend_today(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    saved = await _save_no_spend(user, session)
    key = "no_spend_saved" if saved else "no_spend_has_expense"
    await message.answer(t(user.settings.language, key))


@router.callback_query(F.data == "no_spend:today")
async def cb_no_spend_today(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None:
        return
    saved = await _save_no_spend(user, session)
    key = "no_spend_saved" if saved else "no_spend_has_expense"
    await callback.message.answer(t(user.settings.language, key))
    await callback.answer()


@router.callback_query(F.data.startswith("report:"))
async def cb_report(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.data is None:
        return
    period = callback.data.split(":", 1)[1]
    user = await get_user_from_callback(callback, session)
    if user is None:
        return
    if period == "period":
        service = ReportService(session)
        salary_period, data = await service.salary_period(user)
        if salary_period is None or data is None:
            await callback.message.answer("Активного зарплатного периода пока нет.")
        else:
            premium = await SubscriptionService(session).is_premium(user)
            await callback.message.answer(
                service.render_period_report(
                    salary_period, data, user.settings.timezone, premium=premium
                )
            )
        await callback.answer()
        return
    await _send_report(callback.message, session, period, user=user)
    await callback.answer()


async def _send_report(
    message: Message,
    session: AsyncSession,
    period: str,
    *,
    user=None,
) -> None:
    user = user or await get_user_from_message(message, session)
    if user is None:
        return
    service = ReportService(session)
    premium = await SubscriptionService(session).is_premium(user)
    if period == "alltime" and not premium:
        data = await service.month(user)
        await message.answer(
            service.render_basic_report(data, user.settings.timezone, premium=False)
        )
        return
    if period in {"categories"}:
        period = "month"
    data = {
        "today": service.today,
        "week": service.week,
        "month": service.month,
        "alltime": service.alltime,
    }.get(period, service.month)
    report = await data(user)
    await message.answer(
        service.render_basic_report(report, user.settings.timezone, premium=premium)
    )


async def _save_no_spend(user, session: AsyncSession) -> bool:
    local_today = now_in_timezone(user.settings.timezone).date()
    start, end = current_day_bounds(user.settings.timezone)
    has_expense = await TransactionService(session).has_expense_on_day(user.id, start, end)
    if not has_expense:
        await NoSpendRepository(session).create_or_get(
            user_id=user.id,
            day=local_today,
            timezone=user.settings.timezone,
        )
        return True
    return False
