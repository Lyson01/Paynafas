import hmac
from typing import Any

from app.models import PaymentInvoice, PaymentInvoiceStatus, PaymentProviderCode
from app.services.payments.providers.base import (
    CreatedPayment,
    PaymentProviderUnavailable,
    PaymentStatus,
    WebhookEvent,
)


class ConfiguredExternalPaymentProvider:
    def __init__(
        self,
        *,
        code: PaymentProviderCode,
        provider_name: str,
        enabled: bool,
        secret_key: str,
        public_key: str = "",
        webhook_secret: str = "",
        success_url: str = "",
        cancel_url: str = "",
    ):
        self.code = code
        self.provider_name = provider_name.strip()
        self.enabled = enabled
        self.secret_key = secret_key.strip()
        self.public_key = public_key.strip()
        self.webhook_secret = webhook_secret.strip()
        self.success_url = success_url.strip()
        self.cancel_url = cancel_url.strip()

    @property
    def available(self) -> bool:
        return self.enabled and bool(self.provider_name) and bool(self.secret_key)

    async def create_payment_link(self, invoice: PaymentInvoice) -> CreatedPayment:
        if not self.available:
            raise PaymentProviderUnavailable("Payment provider is not configured")
        raise PaymentProviderUnavailable(
            f"Provider adapter '{self.provider_name}' is not enabled in this build"
        )

    async def verify_webhook(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> WebhookEvent:
        signature = headers.get("x-payment-signature") or headers.get("x-signature") or ""
        signature_valid = bool(self.webhook_secret) and hmac.compare_digest(
            signature, self.webhook_secret
        )
        status = _status_from_payload(payload.get("status"))
        invoice_id = _int_or_none(payload.get("invoice_id"))
        return WebhookEvent(
            signature_valid=signature_valid,
            event_id=str(payload.get("event_id") or payload.get("id") or ""),
            event_type=str(payload.get("event_type") or payload.get("type") or ""),
            provider_invoice_id=(
                str(payload.get("provider_invoice_id") or payload.get("invoice_id"))
                if payload.get("provider_invoice_id") or payload.get("invoice_id")
                else None
            ),
            invoice_id=invoice_id,
            status=status,
            provider_payment_id=(
                str(payload.get("provider_payment_id") or payload.get("payment_id"))
                if payload.get("provider_payment_id") or payload.get("payment_id")
                else None
            ),
            raw=payload,
        )

    async def get_payment_status(self, invoice: PaymentInvoice) -> PaymentStatus:
        if not self.available:
            raise PaymentProviderUnavailable("Payment provider is not configured")
        return PaymentStatus(
            status=invoice.status,
            provider_payment_id=invoice.provider_payment_id,
            raw={"provider": self.provider_name, "invoice_id": invoice.id},
        )


def _status_from_payload(value: object) -> PaymentInvoiceStatus | None:
    if value is None:
        return None
    normalized = str(value).lower()
    mapping = {
        "success": PaymentInvoiceStatus.PAID,
        "succeeded": PaymentInvoiceStatus.PAID,
        "paid": PaymentInvoiceStatus.PAID,
        "failed": PaymentInvoiceStatus.FAILED,
        "cancelled": PaymentInvoiceStatus.CANCELLED,
        "canceled": PaymentInvoiceStatus.CANCELLED,
        "expired": PaymentInvoiceStatus.EXPIRED,
        "refunded": PaymentInvoiceStatus.REFUNDED,
        "pending": PaymentInvoiceStatus.PENDING,
    }
    return mapping.get(normalized)


def _int_or_none(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
