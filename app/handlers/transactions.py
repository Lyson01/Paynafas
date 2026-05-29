from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import (
    after_transaction_keyboard,
    premium_keyboard,
    salary_next_keyboard,
    undo_delete_keyboard,
)
from app.config import settings
from app.handlers.common import get_user_from_callback, get_user_from_message
from app.locales import t
from app.models import TransactionType
from app.repositories.category_repository import CategoryRepository
from app.services.delete_service import DeleteService
from app.services.parser_service import ParserService
from app.services.report_service import ReportService
from app.services.subscription_service import SubscriptionService
from app.services.transaction_service import TransactionService
from app.utils.dates import format_date, format_time
from app.utils.money import format_money
from app.utils.text import html

router = Router(name="transactions")

CATEGORY_EMOJI = {
    "кафе": "☕",
    "транспорт": "🚕",
    "продукты": "🛒",
    "здоровье": "💊",
    "зарплата": "💰",
    "аванс": "💵",
    "другое": "🧾",
}


@router.message(Command("delete_last"))
async def cmd_delete_last(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    batch = await DeleteService(session).delete_last(user.id)
    if batch is None:
        await message.answer(t(user.settings.language, "nothing_to_delete"))
        return
    await message.answer(
        t(user.settings.language, "operation_deleted"),
        reply_markup=undo_delete_keyboard(batch.id),
    )


@router.message(F.text.in_({"➕ Добавить расход", "💰 Добавить доход"}))
async def menu_add_transaction(message: Message) -> None:
    await message.answer(
        "Напиши операцию обычным текстом:\n"
        "кофе 25000\n"
        "зарплата 5000000\n"
        "вчера в 21:30 аптека 70000"
    )


@router.message(F.text & ~F.text.startswith("/"))
async def parse_transaction(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        await message.answer("Напиши /start, чтобы начать.")
        return
    if user.is_blocked:
        return
    if not user.settings.registration_completed:
        await message.answer(t(user.settings.language, "start_new"))
        return
    text = message.text or ""
    parsed = ParserService().parse(
        text,
        default_currency=user.settings.default_currency,
        timezone=user.settings.timezone,
    )
    if parsed.amount is None or parsed.type is None:
        await message.answer(t(user.settings.language, "unknown_amount"))
        return

    subscription = SubscriptionService(session)
    allowed, limit = await subscription.can_add_transaction(user)
    if not allowed:
        await message.answer(
            t(
                user.settings.language,
                "free_limit",
                limit=limit,
                price=settings.premium_monthly_price_uzs,
            ),
            reply_markup=premium_keyboard(),
        )
        return

    result = await TransactionService(session).save_parsed(user, parsed)
    transaction = result.transaction
    if transaction.type == TransactionType.EXPENSE:
        await _reply_expense(message, user, transaction, result.has_active_period, session)
        return

    salary_line = ""
    if parsed.is_salary_related:
        await state.set_state("salary_waiting_next")
        await state.update_data(transaction_id=transaction.id)
        salary_line = t(user.settings.language, "salary_offer")
    await message.answer(
        t(
            user.settings.language,
            "income_saved",
            emoji=_emoji(transaction.category_name),
            title=html(_title(transaction)),
            amount=format_money(transaction.amount, transaction.currency),
            date=format_date(transaction.operation_datetime, user.settings.timezone),
            time=format_time(transaction.operation_datetime, user.settings.timezone),
            salary_line=salary_line,
        ),
        reply_markup=salary_next_keyboard(transaction.id) if parsed.is_salary_related else None,
    )


async def _reply_expense(
    message: Message,
    user,
    transaction,
    has_active_period: bool,
    session: AsyncSession,
) -> None:
    if has_active_period:
        period, balance = await ReportService(session).balance(user)
        balance_line = (
            t(
                user.settings.language,
                "balance_line",
                amount=format_money(
                    balance or Decimal("0"), period.currency if period else transaction.currency
                ),
            )
            if period
            else t(user.settings.language, "no_period_offer")
        )
    else:
        balance_line = t(user.settings.language, "no_period_offer")
    await message.answer(
        t(
            user.settings.language,
            "expense_saved",
            emoji=_emoji(transaction.category_name),
            title=html(_title(transaction)),
            amount=format_money(transaction.amount, transaction.currency),
            date=format_date(transaction.operation_datetime, user.settings.timezone),
            time=format_time(transaction.operation_datetime, user.settings.timezone),
            category=html(transaction.category_name or "другое"),
            balance_line=balance_line,
        ),
        reply_markup=after_transaction_keyboard(transaction.id),
    )


@router.callback_query(F.data.startswith("tx:category:"))
async def choose_category(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None:
        return
    transaction_id = int(callback.data.rsplit(":", 1)[-1])
    categories = await CategoryRepository(session).list_for_type("expense", user.id)
    rows: list[list[InlineKeyboardButton]] = []
    for category in categories[:18]:
        button = InlineKeyboardButton(
            text=f"{category.emoji or ''} {category.name}",
            callback_data=f"tx:set_category:{transaction_id}:{category.slug}",
        )
        if not rows or len(rows[-1]) == 2:
            rows.append([button])
        else:
            rows[-1].append(button)
    await callback.message.answer(
        "Выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tx:set_category:"))
async def set_category(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None:
        return
    _, _, transaction_id, slug = callback.data.split(":", 3)
    transaction = await TransactionService(session).update_category(
        user.id, int(transaction_id), slug
    )
    if transaction:
        await callback.message.answer(f"Категория обновлена: {html(transaction.category_name)}")
    await callback.answer()


def _emoji(category_name: str | None) -> str:
    return CATEGORY_EMOJI.get(category_name or "", "💰" if category_name == "зарплата" else "🧾")


def _title(transaction) -> str:
    source = transaction.comment or transaction.category_name or "операция"
    return source[:1].upper() + source[1:]
