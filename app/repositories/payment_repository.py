from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaymentRequest, PaymentRequestStatus


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        amount: Decimal,
        currency: str,
        receipt_file_id: str | None,
    ) -> PaymentRequest:
        request = PaymentRequest(
            user_id=user_id,
            amount=amount,
            currency=currency,
            status=PaymentRequestStatus.PENDING,
            receipt_file_id=receipt_file_id,
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def get(self, request_id: int) -> PaymentRequest | None:
        result = await self.session.execute(
            select(PaymentRequest).where(PaymentRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def list_pending(self, limit: int = 20) -> list[PaymentRequest]:
        result = await self.session.execute(
            select(PaymentRequest)
            .where(PaymentRequest.status == PaymentRequestStatus.PENDING)
            .order_by(PaymentRequest.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars())

    async def set_status(
        self,
        request: PaymentRequest,
        status: PaymentRequestStatus,
        admin_comment: str | None = None,
    ) -> None:
        request.status = status
        request.admin_comment = admin_comment
        await self.session.flush()
