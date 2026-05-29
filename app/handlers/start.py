from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import location_keyboard, main_menu_keyboard, report_keyboard
from app.locales import t
from app.services.user_service import UserService

router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user, _ = await UserService(session).get_or_create_from_telegram(message.from_user)
    language = user.settings.language
    if user.is_blocked:
        return
    if not user.settings.registration_completed:
        await message.answer(t(language, "start_new"), reply_markup=location_keyboard())
        return
    await message.answer(t(language, "start_existing"), reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user, _ = await UserService(session).get_or_create_from_telegram(message.from_user)
    await message.answer(t(user.settings.language, "help"))


@router.message(F.text == "📊 Отчеты")
async def menu_reports(message: Message) -> None:
    await message.answer("Выбери отчет:", reply_markup=report_keyboard())
