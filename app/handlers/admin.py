from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.admin import AdminFilter
from app.repositories.payment_repository import PaymentRepository
from app.repositories.user_repository import UserRepository
from app.services.admin_service import AdminService

router = Router(name="admin")


@router.message(Command("admin"), AdminFilter())
async def cmd_admin(message: Message, session: AsyncSession, bot: Bot) -> None:
    text = message.text or ""
    parts = text.split(maxsplit=3)
    service = AdminService(session)
    if len(parts) == 1:
        await message.answer(
            "Админ-панель:\n"
            "/admin stats\n"
            "/admin users\n"
            "/admin payments\n"
            "/admin approve PAYMENT_ID\n"
            "/admin reject PAYMENT_ID\n"
            "/admin grant TELEGRAM_ID DAYS\n"
            "/admin revoke TELEGRAM_ID\n"
            "/admin broadcast текст"
        )
        return
    action = parts[1]
    if action == "stats":
        await message.answer(await service.stats())
    elif action == "users":
        users = await UserRepository(session).recent_users(10)
        lines = ["Последние пользователи:"]
        for user in users:
            lines.append(f"{user.telegram_id} @{user.username or '-'} {user.created_at:%d.%m.%Y}")
        await message.answer("\n".join(lines))
    elif action == "payments":
        await _send_pending_payments(message, session)
    elif action == "approve" and len(parts) >= 3:
        request_id = _safe_int(parts[2])
        if request_id is None:
            await message.answer("Неверный ID заявки.")
            return
        telegram_id = await service.approve_payment(request_id, days=30)
        await message.answer("Оплата одобрена." if telegram_id else "Заявка не найдена.")
        if telegram_id:
            await bot.send_message(
                telegram_id, "Оплата подтверждена. Premium активирован на 30 дней."
            )
    elif action == "reject" and len(parts) >= 3:
        request_id = _safe_int(parts[2])
        if request_id is None:
            await message.answer("Неверный ID заявки.")
            return
        telegram_id = await service.reject_payment(request_id)
        await message.answer("Оплата отклонена." if telegram_id else "Заявка не найдена.")
        if telegram_id:
            await bot.send_message(
                telegram_id, "Оплата отклонена. Если это ошибка, отправьте чек еще раз."
            )
    elif action == "grant" and len(parts) >= 4:
        telegram_id = _safe_int(parts[2])
        days = _safe_int(parts[3])
        if telegram_id is None or days is None or days <= 0:
            await message.answer("Формат: /admin grant TELEGRAM_ID DAYS")
            return
        ok = await service.grant_premium(telegram_id, days)
        await message.answer("Premium выдан." if ok else "Пользователь не найден.")
    elif action == "revoke" and len(parts) >= 3:
        telegram_id = _safe_int(parts[2])
        if telegram_id is None:
            await message.answer("Формат: /admin revoke TELEGRAM_ID")
            return
        ok = await service.revoke_premium(telegram_id)
        await message.answer("Premium забран." if ok else "Пользователь не найден.")
    elif action == "broadcast" and len(parts) >= 3:
        body = text.split("broadcast", 1)[1].strip()
        users = await UserRepository(session).list_active_users()
        sent = 0
        for user in users:
            if user.is_blocked:
                continue
            try:
                await bot.send_message(user.telegram_id, body)
                sent += 1
            except Exception:
                continue
        await message.answer(f"Рассылка отправлена: {sent}")
    else:
        await message.answer("Неизвестная админ-команда.")


@router.callback_query(F.data.startswith("admin:payment:"), AdminFilter())
async def cb_payment(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if callback.data is None:
        return
    _, _, action, request_id_text = callback.data.split(":", 3)
    request_id = _safe_int(request_id_text)
    if request_id is None:
        await callback.answer("Неверный ID заявки", show_alert=True)
        return
    if action not in {"approve", "reject"}:
        await callback.answer("Неверное действие", show_alert=True)
        return
    service = AdminService(session)
    if action == "approve":
        telegram_id = await service.approve_payment(request_id, days=30)
        if telegram_id:
            await bot.send_message(
                telegram_id, "Оплата подтверждена. Premium активирован на 30 дней."
            )
        await callback.message.answer("Оплата одобрена.")
    elif action == "reject":
        telegram_id = await service.reject_payment(request_id)
        if telegram_id:
            await bot.send_message(
                telegram_id, "Оплата отклонена. Если это ошибка, отправьте чек еще раз."
            )
        await callback.message.answer("Оплата отклонена.")
    await callback.answer()


async def _send_pending_payments(message: Message, session: AsyncSession) -> None:
    requests = await PaymentRepository(session).list_pending()
    if not requests:
        await message.answer("Pending оплат нет.")
        return
    for request in requests:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Одобрить",
                        callback_data=f"admin:payment:approve:{request.id}",
                    ),
                    InlineKeyboardButton(
                        text="Отклонить",
                        callback_data=f"admin:payment:reject:{request.id}",
                    ),
                ]
            ]
        )
        await message.answer(
            f"Payment #{request.id}\n"
            f"User ID: {request.user_id}\n"
            f"Сумма: {request.amount} {request.currency}\n"
            f"Статус: {request.status}",
            reply_markup=keyboard,
        )


def _safe_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
