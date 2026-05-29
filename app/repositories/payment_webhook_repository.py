from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaymentProviderCode, PaymentWebhookLog


class PaymentWebhookLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        provider: PaymentProviderCode,
        event_id: str | None,
        event_type: str | None,
        payload: dict[str, Any],
        signature_valid: bool,
    ) -> PaymentWebhookLog:
        log = PaymentWebhookLog(
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            signature_valid=signature_valid,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_processed_event(
        self, provider: PaymentProviderCode, event_id: str
    ) -> PaymentWebhookLog | None:
        result = await self.session.execute(
            select(PaymentWebhookLog).where(
                PaymentWebhookLog.provider == provider,
                PaymentWebhookLog.event_id == event_id,
                PaymentWebhookLog.processed.is_(True),
            )
        )
        return result.scalar_one_or_none()
