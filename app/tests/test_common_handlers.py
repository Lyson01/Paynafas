from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.common import get_user_from_callback, get_user_from_message
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_blocked_user_is_hidden_from_message_helpers(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=8001,
        username=None,
        first_name="Blocked",
        last_name=None,
        language_code="ru",
    )
    user.is_blocked = True

    message = SimpleNamespace(from_user=SimpleNamespace(id=8001))

    assert await get_user_from_message(message, session) is None


@pytest.mark.asyncio
async def test_blocked_user_is_hidden_from_callback_helpers(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=8002,
        username=None,
        first_name="Blocked",
        last_name=None,
        language_code="ru",
    )
    user.is_blocked = True

    callback = SimpleNamespace(from_user=SimpleNamespace(id=8002))

    assert await get_user_from_callback(callback, session) is None
