from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import (
    main_menu_keyboard,
    onboarding_confirm_keyboard,
)
from app.handlers.common import get_user_from_callback, get_user_from_message
from app.locales import t
from app.services.location_service import LocationService
from app.services.onboarding_service import OnboardingService
from app.utils.text import html

router = Router(name="onboarding")


@router.message(F.location)
async def handle_location(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None or user.settings.registration_completed or message.location is None:
        return
    result = await LocationService().resolve(
        latitude=message.location.latitude,
        longitude=message.location.longitude,
        telegram_language=user.language_code,
    )
    await OnboardingService(session).apply_location(user, result)
    language_name = {"ru": "Русский", "uz": "O‘zbekcha", "en": "English"}.get(
        user.settings.language, user.settings.language
    )
    await message.answer(
        t(
            user.settings.language,
            "location_ready",
            country=html(user.settings.country_name or "не определена"),
            city=html(user.settings.city or "не определен"),
            currency=html(user.settings.default_currency),
            timezone=html(user.settings.timezone),
            language=html(language_name),
        ),
        reply_markup=onboarding_confirm_keyboard(),
    )


@router.message(F.text.casefold() == "пропустить")
async def skip_location(message: Message, session: AsyncSession) -> None:
    user = await get_user_from_message(message, session)
    if user is None or user.settings.registration_completed:
        return
    await OnboardingService(session).apply_defaults(user)
    language_name = {"ru": "Русский", "uz": "O‘zbekcha", "en": "English"}.get(
        user.settings.language, user.settings.language
    )
    await message.answer(
        t(
            user.settings.language,
            "location_default",
            currency=html(user.settings.default_currency),
            timezone=html(user.settings.timezone),
            language=html(language_name),
        ),
        reply_markup=onboarding_confirm_keyboard(skipped=True),
    )


@router.callback_query(F.data == "onboarding:confirm")
async def confirm_onboarding(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_from_callback(callback, session)
    if user is None:
        return
    await OnboardingService(session).complete(user)
    await callback.message.answer(
        t(user.settings.language, "registration_done"),
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
