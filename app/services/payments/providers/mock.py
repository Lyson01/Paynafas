from typing import Any

from app.config import settings
from app.models import PaymentInvoice, PaymentInvoiceStatus, PaymentProviderCode
from app.services.payments.providers.base import CreatedPayment, PaymentStatus, WebhookEvent


class MockPaymentProvider:
    code = PaymentProviderCode.MOCK

    async def create_payment_link(self, invoice: PaymentInvoice) -> CreatedPayment:
        base_url = settings.public_webhook_base_url.rstrip("/") or "http://localhost:8000"
        provider_invoice_id = f"mock-{invoice.id}"
        return CreatedPayment(
            provider_invoice_id=provider_invoice_id,
            payment_url=f"{base_url}/mock/pay/{invoice.id}",
            metadata={"provider": "mock"},
        )

    async def verify_webhook(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> WebhookEvent:
        status = _status_from_payload(payload.get("status"))
        invoice_id = _int_or_none(payload.get("invoice_id"))
        return WebhookEvent(
            signature_valid=True,
            event_id=str(payload.get("event_id") or f"mock-{invoice_id}-{status}"),
            event_type=str(payload.get("event_type") or "payment.status_changed"),
            provider_invoice_id=(
                str(payload.get("provider_invoice_id"))
                if payload.get("provider_invoice_id") is not None
                else None
            ),
            invoice_id=invoice_id,
            status=status,
            provider_payment_id=(
                str(payload.get("provider_payment_id"))
                if payload.get("provider_payment_id") is not None
                else None
            ),
            raw=payload,
        )

    async def get_payment_status(self, invoice: PaymentInvoice) -> PaymentStatus:
        return PaymentStatus(
            status=invoice.status,
            provider_payment_id=invoice.provider_payment_id,
            raw={"provider": "mock", "invoice_id": invoice.id},
        )


def _status_from_payload(value: object) -> PaymentInvoiceStatus:
    try:
        return PaymentInvoiceStatus(str(value))
    except ValueError:
        return PaymentInvoiceStatus.PENDING


def _int_or_none(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
