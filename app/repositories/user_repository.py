from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Plan, User, UserSettings
from app.utils.text import normalize_language


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).options(selectinload(User.settings)).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).options(selectinload(User.settings)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        is_admin = telegram_id in settings.admin_ids
        if user:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.language_code = language_code
            user.is_admin = user.is_admin or is_admin
            if user.settings is None:
                user.settings = self._default_settings(user, language_code)
            await self.session.flush()
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_admin=is_admin,
            plan=Plan.FREE,
        )
        user.settings = self._default_settings(user, language_code)
        self.session.add(user)
        try:
            await self.session.flush()
            return user, True
        except IntegrityError:
            await self.session.rollback()
            existing = await self.get_by_telegram_id(telegram_id)
            if existing is None:
                raise
            return existing, False

    def _default_settings(self, user: User, language_code: str | None) -> UserSettings:
        language = normalize_language(language_code) or settings.default_language
        return UserSettings(
            user=user,
            timezone=settings.default_timezone,
            default_currency=settings.default_currency,
            language=language,
            daily_reminder_time=settings.daily_reminder_default_time,
        )

    async def list_reminder_candidates(self) -> list[User]:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.settings))
            .where(User.is_blocked.is_(False), UserSettings.user_id == User.id)
        )
        return list(result.scalars().unique())

    async def list_active_users(self) -> list[User]:
        result = await self.session.execute(
            select(User).options(selectinload(User.settings)).where(User.is_blocked.is_(False))
        )
        return list(result.scalars().unique())

    async def recent_users(self, limit: int = 10) -> list[User]:
        result = await self.session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit)
        )
        return list(result.scalars())

    async def count_users(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return int(result.scalar_one())

    async def count_active_since(self, since: datetime) -> int:
        from app.models.transaction import Transaction

        result = await self.session.execute(
            select(func.count(func.distinct(Transaction.user_id))).where(
                Transaction.created_at >= since,
                Transaction.is_deleted.is_(False),
            )
        )
        return int(result.scalar_one())
