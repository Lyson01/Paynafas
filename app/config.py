from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(default="", alias="BOT_TOKEN")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")
    lifetime_premium_telegram_ids: list[int] = Field(
        default_factory=list, alias="LIFETIME_PREMIUM_TELEGRAM_IDS"
    )
    database_url: str = Field(
        default="postgresql+asyncpg://expense_bot:expense_bot@postgres:5432/expense_bot",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    default_timezone: str = Field(default="Asia/Tashkent", alias="DEFAULT_TIMEZONE")
    default_currency: str = Field(default="UZS", alias="DEFAULT_CURRENCY")
    default_language: str = Field(default="ru", alias="DEFAULT_LANGUAGE")

    free_monthly_transaction_limit: int = Field(default=50, alias="FREE_MONTHLY_TRANSACTION_LIMIT")
    premium_monthly_price_uzs: int = Field(default=9900, alias="PREMIUM_MONTHLY_PRICE_UZS")
    premium_yearly_price_uzs: int = Field(default=99000, alias="PREMIUM_YEARLY_PRICE_UZS")
    premium_monthly_price_usd: float = Field(default=1.99, alias="PREMIUM_MONTHLY_PRICE_USD")
    premium_yearly_price_usd: float = Field(default=19.99, alias="PREMIUM_YEARLY_PRICE_USD")

    payment_card_number: str = Field(default="XXXX XXXX XXXX XXXX", alias="PAYMENT_CARD_NUMBER")
    payment_card_owner: str = Field(default="", alias="PAYMENT_CARD_OWNER")
    payments_enabled: bool = Field(default=True, alias="PAYMENTS_ENABLED")

    international_payments_enabled: bool = Field(
        default=True, alias="INTERNATIONAL_PAYMENTS_ENABLED"
    )
    international_payment_provider: str = Field(
        default="mock", alias="INTERNATIONAL_PAYMENT_PROVIDER"
    )
    international_payment_public_key: str = Field(
        default="", alias="INTERNATIONAL_PAYMENT_PUBLIC_KEY"
    )
    international_payment_secret_key: str = Field(
        default="", alias="INTERNATIONAL_PAYMENT_SECRET_KEY"
    )
    international_payment_webhook_secret: str = Field(
        default="", alias="INTERNATIONAL_PAYMENT_WEBHOOK_SECRET"
    )
    international_payment_success_url: str = Field(
        default="", alias="INTERNATIONAL_PAYMENT_SUCCESS_URL"
    )
    international_payment_cancel_url: str = Field(
        default="", alias="INTERNATIONAL_PAYMENT_CANCEL_URL"
    )

    uzbek_payments_enabled: bool = Field(default=True, alias="UZBEK_PAYMENTS_ENABLED")
    uzbek_payment_provider: str = Field(default="mock", alias="UZBEK_PAYMENT_PROVIDER")
    uzbek_payment_merchant_id: str = Field(default="", alias="UZBEK_PAYMENT_MERCHANT_ID")
    uzbek_payment_secret_key: str = Field(default="", alias="UZBEK_PAYMENT_SECRET_KEY")
    uzbek_payment_service_id: str = Field(default="", alias="UZBEK_PAYMENT_SERVICE_ID")
    uzbek_payment_webhook_secret: str = Field(default="", alias="UZBEK_PAYMENT_WEBHOOK_SECRET")
    uzbek_payment_success_url: str = Field(default="", alias="UZBEK_PAYMENT_SUCCESS_URL")
    uzbek_payment_cancel_url: str = Field(default="", alias="UZBEK_PAYMENT_CANCEL_URL")

    delete_undo_ttl_hours: int = Field(default=24, alias="DELETE_UNDO_TTL_HOURS")
    webapp_host: str = Field(default="0.0.0.0", alias="WEBAPP_HOST")
    webapp_port: int = Field(default=8000, alias="WEBAPP_PORT")
    public_webhook_base_url: str = Field(default="", alias="PUBLIC_WEBHOOK_BASE_URL")

    save_raw_location: bool = Field(default=False, alias="SAVE_RAW_LOCATION")
    location_provider: str = Field(default="nominatim", alias="LOCATION_PROVIDER")
    nominatim_user_agent: str = Field(default="expense-salary-bot", alias="NOMINATIM_USER_AGENT")
    enable_reverse_geocoding: bool = Field(default=True, alias="ENABLE_REVERSE_GEOCODING")

    daily_reminder_default_time: str = Field(default="21:30", alias="DAILY_REMINDER_DEFAULT_TIME")
    report_reminder_days_before_salary: int = Field(
        default=1, alias="REPORT_REMINDER_DAYS_BEFORE_SALARY"
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("admin_ids", "lifetime_premium_telegram_ids", mode="before")
    @classmethod
    def parse_int_list(cls, value: Any) -> list[int]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [int(item) for item in value]
        return [int(item.strip()) for item in str(value).split(",") if item.strip()]

    @field_validator("default_currency", "default_language", mode="before")
    @classmethod
    def normalize_upper_lower(cls, value: Any, info: Any) -> str:
        text = str(value or "")
        if info.field_name == "default_currency":
            return text.upper()
        return text.lower()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
