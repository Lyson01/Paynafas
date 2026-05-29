from dataclasses import dataclass
from typing import Any, Protocol

from app.models import PaymentInvoice, PaymentInvoiceStatus, PaymentProviderCode


class PaymentProviderError(RuntimeError):
    """Base payment provider exception."""


class PaymentProviderUnavailable(PaymentProviderError):
    """Raised when a configured provider cannot create or verify payments."""


@dataclass(frozen=True)
class CreatedPayment:
    provider_invoice_id: str
    payment_url: str
    provider_payment_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class PaymentStatus:
    status: PaymentInvoiceStatus
    provider_payment_id: str | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class WebhookEvent:
    signature_valid: bool
    event_id: str | None
    event_type: str | None
    provider_invoice_id: str | None
    invoice_id: int | None
    status: PaymentInvoiceStatus | None
    provider_payment_id: str | None
    raw: dict[str, Any]


class PaymentProvider(Protocol):
    code: PaymentProviderCode

    async def create_payment_link(self, invoice: PaymentInvoice) -> CreatedPayment: ...

    async def verify_webhook(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> WebhookEvent: ...

    async def get_payment_status(self, invoice: PaymentInvoice) -> PaymentStatus: ...
