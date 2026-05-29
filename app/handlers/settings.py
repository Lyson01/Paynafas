from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import (
    currency_keyboard,
    language_keyboard,
    reminders_keyboard,
    settings_keyboard,
    timezone_keyboard,
)
from app.handlers.common import get_user_from_callback, get_user_from_message
from app.locales import t
from app.services.onboarding_service import OnboardingService

router = Router(name="settings")


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    await message.answer(
        t(
            user.settings.language,
            "settings",
            currency=user.settings.default_currency,
            timezone=user.settings.timezone,
            language=user.settings.language,
        ),
        reply_markup=settings_keyboard(),
    )


@router.callback_query(F.data == "settings:language")
async def choose_language(callback: CallbackQuery) -> None:
    await callback.message.answer("Выбери язык:", reply_markup=language_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings:currency")
async def choose_currency(callback: CallbackQuery) -> None:
    await callback.message.answer("Выбери валюту:", reply_markup=currency_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings:timezone")
async def choose_timezone(callback: CallbackQuery) -> None:
    await callback.message.answer("Выбери часовой пояс:", reply_markup=timezone_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings:reminders")
async def choose_reminders(callback: CallbackQuery) -> None:
    await callback.message.answer("Настройки напоминаний:", reply_markup=reminders_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("set:language:"))
async def set_language(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None:
        return
    language = callback.data.rsplit(":", 1)[-1]
    await OnboardingService(session).set_language(user, language)
    await callback.message.answer("Язык обновлен.")
    await callback.answer()


@router.callback_query(F.data.startswith("set:currency:"))
async def set_currency(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None:
        return
    currency = callback.data.rsplit(":", 1)[-1]
    await OnboardingService(session).set_currency(user, currency)
    await callback.message.answer("Валюта обновлена.")
    await callback.answer()


@router.callback_query(F.data.startswith("set:timezone:"))
async def set_timezone(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None:
        return
    timezone = callback.data.split("set:timezone:", 1)[1]
    await OnboardingService(session).set_timezone(user, timezone)
    await callback.message.answer("Часовой пояс обновлен.")
    await callback.answer()
