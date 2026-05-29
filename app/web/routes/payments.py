from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database.session import async_session_maker
from app.models import PaymentInvoiceStatus, PaymentProviderCode
from app.services.payment_service import PaymentService

router = APIRouter()


@router.post("/webhooks/payments/{provider}")
async def payment_webhook(provider: str, request: Request) -> dict[str, Any]:
    try:
        provider_code = PaymentProviderCode(provider)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Unknown provider") from exc

    payload = await request.json()
    headers = {key.lower(): value for key, value in request.headers.items()}
    async with async_session_maker() as session:
        try:
            invoice = await PaymentService(session).process_webhook(provider_code, payload, headers)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return {"ok": True, "invoice_id": invoice.id if invoice else None}


@router.get("/mock/pay/{invoice_id}", response_class=HTMLResponse)
@router.post("/mock/pay/{invoice_id}")
async def mock_pay(invoice_id: int) -> HTMLResponse:
    if not _mock_enabled():
        raise HTTPException(status_code=404, detail="Mock payments are disabled")
    async with async_session_maker() as session:
        try:
            invoice = await PaymentService(session).mock_mark_paid(invoice_id)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    title = (
        "Payment completed"
        if invoice.status == PaymentInvoiceStatus.PAID
        else f"Payment status: {invoice.status.value}"
    )
    return HTMLResponse(
        "<html><body>"
        f"<h1>{title}</h1>"
        f"<p>Invoice #{invoice.id}</p>"
        "<p>You can return to Telegram and press Check payment.</p>"
        "</body></html>"
    )


def _mock_enabled() -> bool:
    return settings.payments_enabled and (
        settings.international_payment_provider == "mock"
        or settings.uzbek_payment_provider == "mock"
    )
