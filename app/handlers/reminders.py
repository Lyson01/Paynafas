from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import reminders_keyboard
from app.handlers.common import get_user_from_callback, get_user_from_message
from app.locales import t

router = Router(name="reminders")


@router.message(Command("reminders"))
async def cmd_reminders(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    status = "включены" if user.settings.daily_reminder_enabled else "выключены"
    await message.answer(
        f"Ежедневные напоминания: {status}\n" f"Время: {user.settings.daily_reminder_time}",
        reply_markup=reminders_keyboard(),
    )


@router.callback_query(F.data == "reminders:disable_daily")
async def disable_daily(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None:
        return
    user.settings.daily_reminder_enabled = False
    await session.flush()
    await callback.message.answer(t(user.settings.language, "reminder_disabled"))
    await callback.answer()
