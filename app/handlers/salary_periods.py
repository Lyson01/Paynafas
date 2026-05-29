from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.common import get_user_from_callback, get_user_from_message
from app.locales import t
from app.repositories.transaction_repository import TransactionRepository
from app.services.parser_service import ParserService
from app.services.salary_period_service import SalaryPeriodService

router = Router(name="salary_periods")


@router.callback_query(F.data == "salary:skip")
async def skip_salary_period(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Ок")


@router.callback_query(F.data.startswith("salary:create:"))
async def create_salary_period_from_callback(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None:
        return
    _, _, transaction_id_text, option = callback.data.split(":", 3)
    transaction = await TransactionRepository(session).get_by_id(int(transaction_id_text), user.id)
    if transaction is None:
        await callback.answer("Операция не найдена")
        return
    option_text = {"month": "через месяц", "25": "25 числа", "skip": "пропустить"}.get(
        option, option
    )
    expected = ParserService().parse_next_salary_date(
        option_text,
        base_datetime=transaction.operation_datetime,
        timezone=user.settings.timezone,
    )
    await SalaryPeriodService(session).create_from_income(transaction, expected)
    await state.clear()
    await callback.message.answer(t(user.settings.language, "period_created"))
    await callback.answer()


@router.message(StateFilter("salary_waiting_next"))
async def create_salary_period_from_text(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    transaction = await TransactionRepository(session).get_by_id(int(transaction_id), user.id)
    if transaction is None:
        await state.clear()
        return
    expected = ParserService().parse_next_salary_date(
        message.text or "пропустить",
        base_datetime=transaction.operation_datetime,
        timezone=user.settings.timezone,
    )
    await SalaryPeriodService(session).create_from_income(transaction, expected)
    await state.clear()
    await message.answer(t(user.settings.language, "period_created"))


@router.message(F.text == "💵 Зарплатный период")
async def salary_period_menu(message: Message) -> None:
    await message.answer(
        "Зарплатный период:\n"
        "— /period посмотреть текущий период\n"
        "— /balance посмотреть остаток\n"
        "— напиши «зарплата 5000000», чтобы начать новый период"
    )
