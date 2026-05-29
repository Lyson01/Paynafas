from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User
from app.services.country_defaults_service import CountryDefaultsService
from app.services.location_service import LocationResult
from app.utils.text import normalize_language


class OnboardingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.country_defaults = CountryDefaultsService()

    async def apply_location(self, user: User, result: LocationResult) -> None:
        user.settings.country_code = result.country_code
        user.settings.country_name = result.country_name
        user.settings.city = result.city
        user.settings.timezone = result.timezone
        user.settings.default_currency = result.currency
        user.settings.language = result.language
        user.settings.date_format = result.date_format
        user.settings.money_format = result.money_format
        user.settings.raw_latitude = result.raw_latitude
        user.settings.raw_longitude = result.raw_longitude
        await self.session.flush()

    async def apply_defaults(self, user: User) -> None:
        language = normalize_language(user.language_code) or settings.default_language
        user.settings.timezone = settings.default_timezone
        user.settings.default_currency = settings.default_currency
        user.settings.language = language
        user.settings.country_code = None
        user.settings.country_name = None
        user.settings.city = None
        await self.session.flush()

    async def complete(self, user: User) -> None:
        user.settings.registration_completed = True
        await self.session.flush()

    async def set_language(self, user: User, language: str) -> None:
        user.settings.language = language
        await self.session.flush()

    async def set_currency(self, user: User, currency: str) -> None:
        user.settings.default_currency = currency.upper()
        await self.session.flush()

    async def set_timezone(self, user: User, timezone: str) -> None:
        user.settings.timezone = timezone
        await self.session.flush()
