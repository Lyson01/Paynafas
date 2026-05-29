import pytest

from app.config import settings
from app.services.country_defaults_service import CountryDefaultsService
from app.services.location_service import LocationService


def test_country_currency_and_language_defaults() -> None:
    service = CountryDefaultsService()

    uz = service.get("UZ")
    assert uz.currency == "UZS"
    assert uz.timezone == "Asia/Tashkent"
    assert service.choose_language("en", "UZ") == "en"
    assert service.choose_language("de", "UZ") == "ru"


def test_unknown_country_fallbacks() -> None:
    defaults = CountryDefaultsService().get("ZZ")

    assert defaults.currency == settings.default_currency
    assert defaults.timezone == settings.default_timezone


@pytest.mark.asyncio
async def test_location_reverse_geocoding_success(monkeypatch: pytest.MonkeyPatch) -> None:
    service = LocationService()
    monkeypatch.setattr(service, "_timezone", lambda lat, lon: "Asia/Tashkent")
    monkeypatch.setattr(
        service,
        "_reverse_geocode",
        lambda lat, lon: ("UZ", "Uzbekistan", "Tashkent"),
    )

    result = await service.resolve(latitude=41.3111, longitude=69.2797, telegram_language="ru")

    assert result.country_code == "UZ"
    assert result.city == "Tashkent"
    assert result.currency == "UZS"
    assert result.timezone == "Asia/Tashkent"


@pytest.mark.asyncio
async def test_location_fallback_when_reverse_geocoding_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = LocationService()
    monkeypatch.setattr(service, "_timezone", lambda lat, lon: "Asia/Tashkent")

    def fail(lat: float, lon: float):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(service, "_reverse_geocode", fail)

    result = await service.resolve(latitude=41.3111, longitude=69.2797, telegram_language="ru")

    assert result.country_code is None
    assert result.currency == settings.default_currency
    assert result.timezone == "Asia/Tashkent"
