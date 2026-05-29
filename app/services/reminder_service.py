import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.locales import t
from app.models import User
from app.repositories.no_spend_repository import NoSpendRepository
from app.repositories.salary_period_repository import SalaryPeriodRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.utils.dates import get_zone, local_day_bounds, parse_hhmm, utc_now

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], redis: Redis | None = None
    ):
        self.session_factory = session_factory
        self.redis = redis

    async def should_send_daily_reminder(
        self, session: AsyncSession, user: User, now: datetime
    ) -> bool:
        settings_obj = user.settings
        if not settings_obj.daily_reminder_enabled or user.is_blocked:
            return False
        local_now = now.astimezone(get_zone(settings_obj.timezone))
        reminder_time = parse_hhmm(
            settings_obj.daily_reminder_time, settings.daily_reminder_default_time
        )
        if local_now.hour != reminder_time.hour or local_now.minute != reminder_time.minute:
            return False
        start, end = local_day_bounds(local_now.date(), settings_obj.timezone)
        transactions = TransactionRepository(session)
        if await transactions.has_expense_between(user.id, start, end):
            return False
        no_spend = NoSpendRepository(session)
        if await no_spend.exists(user.id, local_now.date()):
            return False
        if await self._has_key(f"daily_reminder:{user.id}:{local_now.date().isoformat()}"):
            return False
        return True

    async def send_daily_reminders(self, bot: Bot) -> None:
        async with self.session_factory() as session:
            users = await UserRepository(session).list_active_users()
            now = utc_now()
            for user in users:
                if not user.settings:
                    continue
                try:
                    if not await self.should_send_daily_reminder(session, user, now):
                        continue
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="➕ Добавить расход", callback_data="menu:add_expense"
                                ),
                                InlineKeyboardButton(
                                    text="✅ Сегодня не было трат", callback_data="no_spend:today"
                                ),
                            ],
                            [
                                InlineKeyboardButton(
                                    text="🔕 Не напоминать", callback_data="reminders:disable_daily"
                                )
                            ],
                        ]
                    )
                    await bot.send_message(
                        user.telegram_id,
                        t(user.settings.language, "reminder_daily"),
                        reply_markup=keyboard,
                    )
                    local_now = now.astimezone(get_zone(user.settings.timezone))
                    await self._set_key(
                        f"daily_reminder:{user.id}:{local_now.date().isoformat()}",
                        ttl_seconds=36 * 3600,
                    )
                except Exception:
                    logger.exception("Failed to send daily reminder to user_id=%s", user.id)

    async def send_salary_reminders(self, bot: Bot) -> None:
        async with self.session_factory() as session:
            periods = await SalaryPeriodRepository(session).list_active_with_expected_salary()
            users = UserRepository(session)
            now = utc_now()
            for period in periods:
                user = await users.get_by_id(period.user_id)
                if user is None or user.is_blocked or not user.settings.report_reminder_enabled:
                    continue
                expected = period.expected_next_salary_datetime
                if expected is None:
                    continue
                remind_at = expected - timedelta(days=settings.report_reminder_days_before_salary)
                local_now = now.astimezone(get_zone(user.settings.timezone))
                local_remind = remind_at.astimezone(local_now.tzinfo)
                if local_now.date() != local_remind.date() or local_now.hour != local_remind.hour:
                    continue
                key = f"salary_reminder:{period.id}:{local_now.date().isoformat()}"
                if await self._has_key(key):
                    continue
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Краткий отчет", callback_data="report:period"
                            ),
                            InlineKeyboardButton(
                                text="По категориям", callback_data="report:categories"
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                text="Экспорт Excel", callback_data="export:xlsx:salary"
                            ),
                        ],
                    ]
                )
                try:
                    await bot.send_message(
                        user.telegram_id,
                        t(user.settings.language, "salary_reminder"),
                        reply_markup=keyboard,
                    )
                    await self._set_key(key, ttl_seconds=48 * 3600)
                except Exception:
                    logger.exception("Failed to send salary reminder to user_id=%s", user.id)

    async def _has_key(self, key: str) -> bool:
        if self.redis is None:
            return False
        return bool(await self.redis.exists(key))

    async def _set_key(self, key: str, ttl_seconds: int) -> None:
        if self.redis is not None:
            await self.redis.set(key, "1", ex=ttl_seconds)
