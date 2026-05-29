from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import DeleteBatch, DeleteBatchItem, DeleteType, Transaction


class DeleteBatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        delete_type: DeleteType,
        transactions: list[Transaction],
        expires_at: datetime,
    ) -> DeleteBatch:
        batch = DeleteBatch(
            user_id=user_id,
            delete_type=delete_type,
            transactions_count=len(transactions),
            expires_at=expires_at,
        )
        self.session.add(batch)
        await self.session.flush()
        for transaction in transactions:
            self.session.add(
                DeleteBatchItem(delete_batch_id=batch.id, transaction_id=transaction.id)
            )
        await self.session.flush()
        return batch

    async def get(self, batch_id: int, user_id: int | None = None) -> DeleteBatch | None:
        query = (
            select(DeleteBatch)
            .options(selectinload(DeleteBatch.items).selectinload(DeleteBatchItem.transaction))
            .where(DeleteBatch.id == batch_id)
        )
        if user_id is not None:
            query = query.where(DeleteBatch.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_last_restorable(self, user_id: int, now: datetime) -> DeleteBatch | None:
        result = await self.session.execute(
            select(DeleteBatch)
            .options(selectinload(DeleteBatch.items).selectinload(DeleteBatchItem.transaction))
            .where(
                DeleteBatch.user_id == user_id,
                DeleteBatch.restored_at.is_(None),
                DeleteBatch.expires_at > now,
            )
            .order_by(DeleteBatch.created_at.desc(), DeleteBatch.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
