from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import (
    payment_invoice_keyboard,
    payment_methods_keyboard,
    premium_active_keyboard,
    premium_keyboard,
)
from app.config import settings
from app.handlers.common import get_user_from_callback, get_user_from_message
from app.models import PaymentInvoiceStatus, PaymentMethod, PaymentPlan
from app.services.payment_service import PaymentService
from app.services.payment_service_errors import PaymentUnavailableError
from app.services.subscription_service import SubscriptionService
from app.utils.dates import format_date
from app.utils.money import format_money

router = Router(name="premium")

PREMIUM_FEATURES = (
    "Premium открывает:\n"
    "— безлимитные записи\n"
    "— полный отчет от зарплаты до зарплаты\n"
    "— экспорт Excel\n"
    "— прогноз, хватит ли денег до зарплаты\n"
    "— история за все время\n"
    "— расширенную статистику"
)


@router.message(Command("premium"))
@router.message(F.text == "⭐ Premium")
async def cmd_premium(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    await _send_premium_menu(message, session, user)


@router.callback_query(F.data == "premium:features")
async def premium_features(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer(PREMIUM_FEATURES)
    await callback.answer()


@router.callback_query(F.data.startswith("premium:plan:"))
async def choose_plan(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None or callback.message is None:
        return
    plan_value = callback.data.rsplit(":", 1)[-1]
    try:
        plan = PaymentPlan(plan_value)
    except ValueError:
        await callback.answer("Тариф недоступен.", show_alert=True)
        return

    service = PaymentService(session)
    methods = service.available_methods(user)
    if not methods:
        await callback.message.answer("Онлайн-оплата временно недоступна. Попробуй позже.")
        await callback.answer()
        return

    await state.update_data(payment_plan=plan.value)
    amount, currency = service.price_for(user, plan)
    await callback.message.answer(
        "Выбери способ оплаты:\n\n"
        f"Тариф: {_plan_title(plan)}\n"
        f"Сумма: {format_money(amount, currency)}",
        reply_markup=payment_methods_keyboard(
            show_international=any(
                option.method == PaymentMethod.VISA_MASTERCARD for option in methods
            ),
            show_uzbek=any(option.method == PaymentMethod.UZCARD_HUMO for option in methods),
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("payment:method:"))
async def choose_payment_method(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None or callback.message is None:
        return
    state_data = await state.get_data()
    plan_value = state_data.get("payment_plan")
    if not plan_value:
        await callback.message.answer("Это действие уже недоступно. Открой /premium заново.")
        await callback.answer()
        return

    try:
        plan = PaymentPlan(str(plan_value))
        method = PaymentMethod(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer("Способ оплаты недоступен.", show_alert=True)
        return

    try:
        invoice = await PaymentService(session).create_invoice(user, plan, method)
    except PaymentUnavailableError:
        await callback.message.answer("Этот способ оплаты временно недоступен. Выбери другой.")
        await callback.answer()
        return

    await state.clear()
    await callback.message.answer(
        _invoice_text(invoice),
        reply_markup=payment_invoice_keyboard(invoice.id, invoice.payment_url),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("payment:check:"))
async def check_payment(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None or callback.message is None:
        return
    invoice_id = int(callback.data.rsplit(":", 1)[-1])
    invoice = await PaymentService(session).check_invoice(user, invoice_id)
    if invoice is None:
        await callback.message.answer("Счет не найден.")
        await callback.answer()
        return
    if invoice.status == PaymentInvoiceStatus.PAID:
        until = (
            format_date(user.premium_until, user.settings.timezone) if user.premium_until else ""
        )
        await callback.message.answer(f"Оплата прошла успешно.\nPremium активирован до {until}.")
    elif invoice.status == PaymentInvoiceStatus.PENDING:
        await callback.message.answer("Оплата пока не найдена. Проверь еще раз через минуту.")
    elif invoice.status == PaymentInvoiceStatus.EXPIRED:
        await callback.message.answer("Счет истек. Открой /premium и создай новый счет.")
    else:
        await callback.message.answer("Оплата не прошла. Можно создать новый счет в /premium.")
    await callback.answer()


@router.callback_query(F.data.startswith("payment:cancel"))
async def cancel_payment(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None or callback.message is None:
        return
    parts = callback.data.split(":")
    if len(parts) == 3:
        await PaymentService(session).cancel_invoice(user.id, int(parts[2]))
    await state.clear()
    await callback.message.answer("Оплата отменена.")
    await callback.answer()


@router.message(Command("mock_pay"))
async def mock_pay(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None or (not user.is_admin and user.telegram_id not in settings.admin_ids):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /mock_pay invoice_id")
        return
    invoice = await PaymentService(session).mock_mark_paid(int(parts[1]))
    if invoice is None:
        await message.answer("Счет не найден.")
        return
    await message.answer(f"Mock-оплата проведена. Invoice #{invoice.id}: {invoice.status.value}.")


async def _send_premium_menu(message: Message, session: AsyncSession, user) -> None:
    service = PaymentService(session)
    subscription = SubscriptionService(session)
    month_amount, month_currency = service.price_for(user, PaymentPlan.PREMIUM_MONTH)
    year_amount, year_currency = service.price_for(user, PaymentPlan.PREMIUM_YEAR)
    month_label = f"1 месяц — {format_money(month_amount, month_currency)}"
    year_label = f"1 год — {format_money(year_amount, year_currency)}"

    if await subscription.is_premium(user):
        until = (
            format_date(user.premium_until, user.settings.timezone) if user.premium_until else ""
        )
        await message.answer(
            f"У тебя активен Premium до {until}.",
            reply_markup=premium_active_keyboard(
                month_label=f"Продлить на месяц — {format_money(month_amount, month_currency)}",
                year_label=f"Продлить на год — {format_money(year_amount, year_currency)}",
            ),
        )
        return

    await message.answer(
        f"{PREMIUM_FEATURES}\n\nВыбери тариф:",
        reply_markup=premium_keyboard(month_label=month_label, year_label=year_label),
    )


def _invoice_text(invoice) -> str:
    return (
        "Счет создан.\n\n"
        f"Тариф: {_plan_title(invoice.plan)}\n"
        f"Сумма: {format_money(Decimal(invoice.amount), invoice.currency)}\n"
        f"Способ оплаты: {_method_title(invoice.payment_method)}\n\n"
        "Нажми кнопку ниже для оплаты."
    )


def _plan_title(plan: PaymentPlan) -> str:
    return "Premium на 1 год" if plan == PaymentPlan.PREMIUM_YEAR else "Premium на 1 месяц"


def _method_title(method: PaymentMethod) -> str:
    if method == PaymentMethod.UZCARD_HUMO:
        return "Uzcard / Humo"
    return "Visa / Mastercard"
