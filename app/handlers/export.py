from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import export_keyboard
from app.handlers.common import get_user_from_callback, get_user_from_message
from app.locales import t
from app.services.export_service import ExportService
from app.services.subscription_service import SubscriptionService

router = Router(name="export")


@router.message(Command("export"))
async def cmd_export(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None:
        return
    if not await SubscriptionService(session).is_premium(user):
        await message.answer(t(user.settings.language, "premium_required"))
        return
    await message.answer("Выбери формат и период:", reply_markup=export_keyboard())


@router.callback_query(F.data.startswith("export:"))
async def cb_export(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None or callback.data is None:
        return
    if not await SubscriptionService(session).is_premium(user):
        await callback.message.answer(t(user.settings.language, "premium_required"))
        await callback.answer()
        return
    _, fmt, period = callback.data.split(":", 2)
    if fmt not in {"csv", "xlsx"} or period not in {"today", "week", "month", "salary", "alltime"}:
        await callback.answer("Неверный формат экспорта", show_alert=True)
        return
    service = ExportService(session)
    if fmt == "xlsx":
        content, filename = await service.xlsx_file(user, period)
    else:
        content, filename = await service.csv_file(user, period)
    await callback.message.answer_document(BufferedInputFile(content, filename=filename))
    await callback.answer()
