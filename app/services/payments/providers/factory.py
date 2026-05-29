from app.config import settings
from app.models import PaymentMethod, PaymentProviderCode
from app.services.payments.providers.base import PaymentProvider
from app.services.payments.providers.external import ConfiguredExternalPaymentProvider
from app.services.payments.providers.mock import MockPaymentProvider

SUPPORTED_EXTERNAL_PROVIDERS: set[str] = set()


class PaymentProviderFactory:
    def provider_for_method(self, method: PaymentMethod) -> PaymentProvider:
        if method == PaymentMethod.UZCARD_HUMO:
            if settings.uzbek_payment_provider == "mock":
                return MockPaymentProvider()
            return ConfiguredExternalPaymentProvider(
                code=PaymentProviderCode.UZBEK_CARD,
                provider_name=settings.uzbek_payment_provider,
                enabled=settings.uzbek_payments_enabled,
                public_key=settings.uzbek_payment_merchant_id,
                secret_key=settings.uzbek_payment_secret_key,
                webhook_secret=settings.uzbek_payment_webhook_secret,
                success_url=settings.uzbek_payment_success_url,
                cancel_url=settings.uzbek_payment_cancel_url,
            )
        if settings.international_payment_provider == "mock":
            return MockPaymentProvider()
        return ConfiguredExternalPaymentProvider(
            code=PaymentProviderCode.INTERNATIONAL_CARD,
            provider_name=settings.international_payment_provider,
            enabled=settings.international_payments_enabled,
            public_key=settings.international_payment_public_key,
            secret_key=settings.international_payment_secret_key,
            webhook_secret=settings.international_payment_webhook_secret,
            success_url=settings.international_payment_success_url,
            cancel_url=settings.international_payment_cancel_url,
        )

    def provider_by_code(self, code: PaymentProviderCode) -> PaymentProvider:
        if code == PaymentProviderCode.MOCK:
            return MockPaymentProvider()
        if code == PaymentProviderCode.UZBEK_CARD:
            return ConfiguredExternalPaymentProvider(
                code=PaymentProviderCode.UZBEK_CARD,
                provider_name=settings.uzbek_payment_provider,
                enabled=settings.uzbek_payments_enabled,
                public_key=settings.uzbek_payment_merchant_id,
                secret_key=settings.uzbek_payment_secret_key,
                webhook_secret=settings.uzbek_payment_webhook_secret,
                success_url=settings.uzbek_payment_success_url,
                cancel_url=settings.uzbek_payment_cancel_url,
            )
        return ConfiguredExternalPaymentProvider(
            code=PaymentProviderCode.INTERNATIONAL_CARD,
            provider_name=settings.international_payment_provider,
            enabled=settings.international_payments_enabled,
            public_key=settings.international_payment_public_key,
            secret_key=settings.international_payment_secret_key,
            webhook_secret=settings.international_payment_webhook_secret,
            success_url=settings.international_payment_success_url,
            cancel_url=settings.international_payment_cancel_url,
        )

    def is_method_available(self, method: PaymentMethod) -> bool:
        if not settings.payments_enabled:
            return False
        if method == PaymentMethod.UZCARD_HUMO:
            return settings.uzbek_payments_enabled and self._provider_available(
                settings.uzbek_payment_provider, settings.uzbek_payment_secret_key
            )
        return settings.international_payments_enabled and self._provider_available(
            settings.international_payment_provider,
            settings.international_payment_secret_key,
        )

    def _provider_available(self, provider_name: str, secret_key: str) -> bool:
        provider = provider_name.strip()
        if provider == "mock":
            return True
        return bool(secret_key.strip()) and provider in SUPPORTED_EXTERNAL_PROVIDERS
