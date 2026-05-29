import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_user_by_telegram_id(session: AsyncSession) -> None:
    user, created = await UserRepository(session).get_or_create(
        telegram_id=6001,
        username="tester",
        first_name="Test",
        last_name=None,
        language_code="ru",
    )

    assert created is True
    assert user.telegram_id == 6001
    assert user.settings.registration_completed is False


@pytest.mark.asyncio
async def test_repeat_start_finds_existing_user(session: AsyncSession) -> None:
    repo = UserRepository(session)
    first, created_first = await repo.get_or_create(
        telegram_id=6002,
        username="first",
        first_name="First",
        last_name=None,
        language_code="ru",
    )
    second, created_second = await repo.get_or_create(
        telegram_id=6002,
        username="second",
        first_name="Second",
        last_name=None,
        language_code="ru",
    )

    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert second.username == "second"


@pytest.mark.asyncio
async def test_user_data_is_loaded_from_database(
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    async with session_maker() as session:
        user, _ = await UserRepository(session).get_or_create(
            telegram_id=6003,
            username=None,
            first_name="Persisted",
            last_name=None,
            language_code="ru",
        )
        user.settings.registration_completed = True
        await session.commit()
        user_id = user.id

    async with session_maker() as session:
        loaded = await UserRepository(session).get_by_telegram_id(6003)

    assert loaded is not None
    assert loaded.id == user_id
    assert loaded.settings.registration_completed is True
