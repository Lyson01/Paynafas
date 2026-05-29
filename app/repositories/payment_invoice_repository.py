from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    PaymentInvoice,
    PaymentInvoiceStatus,
    PaymentMethod,
    PaymentPlan,
    PaymentProviderCode,
)


class PaymentInvoiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        provider: PaymentProviderCode,
        payment_method: PaymentMethod,
        plan: PaymentPlan,
        amount: Decimal,
        currency: str,
        expires_at: datetime,
    ) -> PaymentInvoice:
        invoice = PaymentInvoice(
            user_id=user_id,
            provider=provider,
            payment_method=payment_method,
            plan=plan,
            amount=amount,
            currency=currency,
            status=PaymentInvoiceStatus.PENDING,
            expires_at=expires_at,
        )
        self.session.add(invoice)
        await self.session.flush()
        return invoice

    async def get(self, invoice_id: int, user_id: int | None = None) -> PaymentInvoice | None:
        query = select(PaymentInvoice).where(PaymentInvoice.id == invoice_id)
        if user_id is not None:
            query = query.where(PaymentInvoice.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_for_update(self, invoice_id: int) -> PaymentInvoice | None:
        result = await self.session.execute(
            select(PaymentInvoice).where(PaymentInvoice.id == invoice_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_provider_invoice_id(self, provider_invoice_id: str) -> PaymentInvoice | None:
        result = await self.session.execute(
            select(PaymentInvoice).where(PaymentInvoice.provider_invoice_id == provider_invoice_id)
        )
        return result.scalar_one_or_none()

    async def list_user(self, user_id: int, limit: int = 10) -> list[PaymentInvoice]:
        result = await self.session.execute(
            select(PaymentInvoice)
            .where(PaymentInvoice.user_id == user_id)
            .order_by(PaymentInvoice.created_at.desc(), PaymentInvoice.id.desc())
            .limit(limit)
        )
        return list(result.scalars())
