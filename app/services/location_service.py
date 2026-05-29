import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal

from timezonefinder import TimezoneFinder

from app.config import settings
from app.services.country_defaults_service import CountryDefaultsService

logger = logging.getLogger(__name__)


@dataclass
class LocationResult:
    country_code: str | None
    country_name: str | None
    city: str | None
    timezone: str
    currency: str
    language: str
    date_format: str | None
    money_format: str | None
    raw_latitude: Decimal | None = None
    raw_longitude: Decimal | None = None


class LocationService:
    def __init__(self, country_defaults: CountryDefaultsService | None = None):
        self.country_defaults = country_defaults or CountryDefaultsService()
        self.timezone_finder = TimezoneFinder()

    async def resolve(
        self,
        *,
        latitude: float,
        longitude: float,
        telegram_language: str | None = None,
    ) -> LocationResult:
        timezone = self._timezone(latitude, longitude) or settings.default_timezone
        country_code: str | None = None
        country_name: str | None = None
        city: str | None = None

        if settings.enable_reverse_geocoding:
            try:
                country_code, country_name, city = await asyncio.to_thread(
                    self._reverse_geocode, latitude, longitude
                )
            except Exception:
                logger.exception("Reverse geocoding failed")

        defaults = self.country_defaults.get(country_code)
        language = self.country_defaults.choose_language(telegram_language, country_code)

        return LocationResult(
            country_code=country_code,
            country_name=country_name or defaults.country_name,
            city=city,
            timezone=timezone or defaults.timezone,
            currency=defaults.currency,
            language=language,
            date_format=defaults.date_format,
            money_format=defaults.money_format,
            raw_latitude=Decimal(str(latitude)) if settings.save_raw_location else None,
            raw_longitude=Decimal(str(longitude)) if settings.save_raw_location else None,
        )

    def _timezone(self, latitude: float, longitude: float) -> str | None:
        try:
            return self.timezone_finder.timezone_at(lat=latitude, lng=longitude)
        except Exception:
            logger.exception("Timezone lookup failed")
            return None

    def _reverse_geocode(
        self, latitude: float, longitude: float
    ) -> tuple[str | None, str | None, str | None]:
        if settings.location_provider != "nominatim":
            return None, None, None
        from geopy.geocoders import Nominatim

        geolocator = Nominatim(user_agent=settings.nominatim_user_agent, timeout=5)
        location = geolocator.reverse((latitude, longitude), language="en", addressdetails=True)
        if location is None:
            return None, None, None
        address = location.raw.get("address", {})
        country_code = str(address.get("country_code") or "").upper() or None
        country_name = address.get("country")
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("state")
        )
        return country_code, country_name, city
