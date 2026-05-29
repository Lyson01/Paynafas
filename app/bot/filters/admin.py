from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.user_repository import UserRepository


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        if message.from_user is None:
            return False
        if message.from_user.id in settings.admin_ids:
            return True
        user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
        return bool(user and user.is_admin)
