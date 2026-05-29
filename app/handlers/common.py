from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.user_repository import UserRepository


async def get_user_from_message(message: Message, session: AsyncSession) -> User | None:
    if message.from_user is None:
        return None
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user and user.is_blocked:
        return None
    return user


async def get_user_from_callback(callback: CallbackQuery, session: AsyncSession) -> User | None:
    if callback.from_user is None:
        return None
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user and user.is_blocked:
        return None
    return user
