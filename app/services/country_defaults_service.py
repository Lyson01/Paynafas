from dataclasses import dataclass

from app.config import settings
from app.utils.constants import SUPPORTED_LANGUAGES
from app.utils.text import normalize_language


@dataclass(frozen=True)
class CountryDefaults:
    country_code: str | None
    country_name: str | None
    currency: str
    timezone: str
    supported_languages: tuple[str, ...]
    date_format: str = "%d.%m.%Y"
    money_format: str = "{amount} {currency}"


class CountryDefaultsService:
    EU_COUNTRIES = {
        "AT",
        "BE",
        "BG",
        "CY",
        "CZ",
        "DE",
        "DK",
        "EE",
        "ES",
        "FI",
        "FR",
        "GR",
        "HR",
        "HU",
        "IE",
        "IT",
        "LT",
        "LU",
        "LV",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SE",
        "SI",
        "SK",
    }

    COUNTRIES: dict[str, CountryDefaults] = {
        "UZ": CountryDefaults("UZ", "Uzbekistan", "UZS", "Asia/Tashkent", ("ru", "uz")),
        "RU": CountryDefaults("RU", "Russia", "RUB", "Europe/Moscow", ("ru",)),
        "KZ": CountryDefaults("KZ", "Kazakhstan", "KZT", "Asia/Almaty", ("ru",)),
        "KG": CountryDefaults("KG", "Kyrgyzstan", "KGS", "Asia/Bishkek", ("ru",)),
        "TJ": CountryDefaults("TJ", "Tajikistan", "TJS", "Asia/Dushanbe", ("ru",)),
        "US": CountryDefaults("US", "United States", "USD", "America/New_York", ("en",)),
        "GB": CountryDefaults("GB", "United Kingdom", "GBP", "Europe/London", ("en",)),
        "TR": CountryDefaults("TR", "Turkey", "TRY", "Europe/Istanbul", ("en",)),
        "AE": CountryDefaults("AE", "United Arab Emirates", "AED", "Asia/Dubai", ("en",)),
    }

    def get(self, country_code: str | None) -> CountryDefaults:
        code = (country_code or "").upper()
        if code in self.COUNTRIES:
            return self.COUNTRIES[code]
        if code in self.EU_COUNTRIES:
            return CountryDefaults(code, "European Union", "EUR", "Europe/Berlin", ("en",))
        return CountryDefaults(
            country_code=code or None,
            country_name=None,
            currency=settings.default_currency,
            timezone=settings.default_timezone,
            supported_languages=(settings.default_language,),
        )

    def choose_language(
        self, telegram_language: str | None, country_code: str | None = None
    ) -> str:
        telegram = normalize_language(telegram_language)
        if telegram and telegram in SUPPORTED_LANGUAGES:
            return telegram
        defaults = self.get(country_code)
        if defaults.supported_languages:
            return defaults.supported_languages[0]
        return settings.default_language
