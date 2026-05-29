import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from redis.asyncio import Redis

from app.bot.loader import create_bot, create_dispatcher
from app.bot.middlewares.database import DatabaseSessionMiddleware
from app.config import settings
from app.database.session import async_session_maker, engine
from app.handlers import (
    admin,
    deletions,
    errors,
    export,
    onboarding,
    premium,
    reminders,
    reports,
    salary_periods,
    start,
    transactions,
)
from app.handlers import (
    settings as settings_handlers,
)
from app.services.reminder_service import ReminderService


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )


async def on_startup(bot: Bot, dispatcher: Dispatcher) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="help", description="Помощь"),
            BotCommand(command="today", description="Отчет за сегодня"),
            BotCommand(command="week", description="Отчет за неделю"),
            BotCommand(command="month", description="Отчет за месяц"),
            BotCommand(command="period", description="Зарплатный период"),
            BotCommand(command="balance", description="Остаток от зарплаты"),
            BotCommand(command="history", description="История операций"),
            BotCommand(command="delete_last", description="Удалить последнюю операцию"),
            BotCommand(command="delete", description="Меню удаления записей"),
            BotCommand(command="clear", description="Массовое удаление записей"),
            BotCommand(command="undo_delete", description="Восстановить последнее удаление"),
            BotCommand(command="no_spend_today", description="Сегодня без трат"),
            BotCommand(command="reminders", description="Напоминания"),
            BotCommand(command="settings", description="Настройки"),
            BotCommand(command="premium", description="Premium"),
            BotCommand(command="export", description="Экспорт"),
        ]
    )
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    reminder_service = ReminderService(async_session_maker, redis)
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        reminder_service.send_daily_reminders,
        trigger="interval",
        minutes=1,
        args=[bot],
        id="daily_reminders",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        reminder_service.send_salary_reminders,
        trigger="interval",
        minutes=5,
        args=[bot],
        id="salary_reminders",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    dispatcher["scheduler"] = scheduler
    dispatcher["redis"] = redis
    logging.getLogger(__name__).info("Bot started")


async def on_shutdown(dispatcher: Dispatcher) -> None:
    scheduler: AsyncIOScheduler | None = dispatcher.workflow_data.get("scheduler")
    redis: Redis | None = dispatcher.workflow_data.get("redis")
    if scheduler:
        scheduler.shutdown(wait=False)
    if redis:
        await redis.aclose()
    await engine.dispose()
    logging.getLogger(__name__).info("Bot stopped")


def setup_dispatcher(dp: Dispatcher) -> None:
    async def startup(bot: Bot, **_: object) -> None:
        await on_startup(bot, dp)

    async def shutdown(**_: object) -> None:
        await on_shutdown(dp)

    dp.update.middleware(DatabaseSessionMiddleware())
    dp.include_router(start.router)
    dp.include_router(onboarding.router)
    dp.include_router(settings_handlers.router)
    dp.include_router(reminders.router)
    dp.include_router(reports.router)
    dp.include_router(export.router)
    dp.include_router(premium.router)
    dp.include_router(deletions.router)
    dp.include_router(admin.router)
    dp.include_router(salary_periods.router)
    dp.include_router(transactions.router)
    dp.include_router(errors.router)
    dp.startup.register(startup)
    dp.shutdown.register(shutdown)


async def main() -> None:
    configure_logging()
    bot = create_bot()
    dp = create_dispatcher()
    setup_dispatcher(dp)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
