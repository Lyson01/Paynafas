import asyncio
from pathlib import Path

import pytest
from aiogram import Bot

from app.bot.loader import create_dispatcher
from app.config import Settings
from app.main import setup_dispatcher


async def close_dispatcher(dispatcher) -> None:
    for router in list(dispatcher.sub_routers):
        router._parent_router = None
    dispatcher.sub_routers.clear()
    await dispatcher.storage.close()


def test_env_example_matches_settings_aliases() -> None:
    aliases = {field.alias or name for name, field in Settings.model_fields.items()}
    example_keys = {
        line.split("=", 1)[0]
        for line in Path(".env.example").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }

    assert example_keys == aliases


def test_database_url_normalizes_railway_postgres_scheme() -> None:
    settings = Settings(
        BOT_TOKEN="token",
        DATABASE_URL="postgresql://user:pass@host:5432/db",
        REDIS_URL="redis://host:6379/0",
    )

    assert settings.database_url == "postgresql+asyncpg://user:pass@host:5432/db"


@pytest.mark.asyncio
async def test_handlers_are_registered() -> None:
    dispatcher = create_dispatcher()
    try:
        setup_dispatcher(dispatcher)

        assert [router.name for router in dispatcher.sub_routers] == [
            "start",
            "onboarding",
            "settings",
            "reminders",
            "reports",
            "export",
            "premium",
            "deletions",
            "admin",
            "salary_periods",
            "transactions",
            "errors",
        ]
    finally:
        await close_dispatcher(dispatcher)


@pytest.mark.asyncio
async def test_startup_shutdown_callbacks_accept_aiogram_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_set_my_commands(
        self: Bot,
        commands: list[object],
        *args: object,
        **kwargs: object,
    ) -> None:
        assert len(commands) >= 10

    monkeypatch.setattr(Bot, "set_my_commands", fake_set_my_commands)
    dispatcher = create_dispatcher()
    bot = Bot("123456:ABCDEFabcdef1234567890")
    try:
        setup_dispatcher(dispatcher)
        await dispatcher.emit_startup(bot=bot)
        assert "scheduler" in dispatcher.workflow_data
        assert "redis" in dispatcher.workflow_data
        await dispatcher.emit_shutdown(bot=bot)
    finally:
        await close_dispatcher(dispatcher)
        await bot.session.close()
        await asyncio.sleep(0)
