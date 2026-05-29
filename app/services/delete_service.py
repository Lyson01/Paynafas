from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import DeleteBatch, DeleteType, Transaction, User
from app.repositories.delete_batch_repository import DeleteBatchRepository
from app.repositories.salary_period_repository import SalaryPeriodRepository
from app.repositories.transaction_repository import TransactionRepository
from app.utils.dates import (
    current_day_bounds,
    current_month_bounds,
    current_week_bounds,
    utc_now,
)


@dataclass
class DeletePreview:
    delete_type: DeleteType
    count: int
    transactions: list[Transaction]
    title: str
    period: str


class DeleteService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.transactions = TransactionRepository(session)
        self.batches = DeleteBatchRepository(session)
        self.periods = SalaryPeriodRepository(session)

    async def preview(self, user: User, delete_type: DeleteType) -> DeletePreview:
        start = end = None
        title = "записи"
        period = "все время"
        salary_period_id = None

        if delete_type == DeleteType.TODAY:
            start, end = current_day_bounds(user.settings.timezone)
            title = "все записи за сегодня"
            period = start.strftime("%d.%m.%Y")
        elif delete_type == DeleteType.WEEK:
            start, end = current_week_bounds(user.settings.timezone)
            title = "все записи за неделю"
            week_end = end - timedelta(days=1)
            period = f"{start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}"
        elif delete_type == DeleteType.MONTH:
            start, end = current_month_bounds(user.settings.timezone)
            title = "все записи за месяц"
            period = start.strftime("%m.%Y")
        elif delete_type == DeleteType.PERIOD:
            active_period = await self.periods.get_active(user.id)
            if active_period is None:
                return DeletePreview(delete_type, 0, [], "текущий зарплатный период", "")
            salary_period_id = active_period.id
            title = "все записи текущего зарплатного периода"
            period = active_period.start_datetime.strftime("%d.%m.%Y")
        elif delete_type == DeleteType.ALL:
            title = "ВСЕ твои записи"
            period = "вся история"

        if delete_type == DeleteType.PERIOD and salary_period_id is not None:
            items = await self.transactions.list_for_period(user.id, salary_period_id)
        else:
            items = await self.transactions.list_between(user_id=user.id, start=start, end=end)
        return DeletePreview(delete_type, len(items), items, title, period)

    async def delete_last(self, user_id: int) -> DeleteBatch | None:
        transaction = await self.transactions.get_last(user_id)
        if transaction is None:
            return None
        return await self.delete_transactions(user_id, [transaction], DeleteType.SINGLE)

    async def delete_single(self, user_id: int, transaction_id: int) -> DeleteBatch | None:
        transaction = await self.transactions.get_by_id(transaction_id, user_id)
        if transaction is None or transaction.is_deleted:
            return None
        return await self.delete_transactions(user_id, [transaction], DeleteType.SINGLE)

    async def delete_selected(self, user_id: int, transaction_ids: list[int]) -> DeleteBatch | None:
        items = await self.transactions.list_by_ids(user_id, transaction_ids)
        if not items:
            return None
        return await self.delete_transactions(user_id, items, DeleteType.CUSTOM)

    async def delete_by_type(self, user: User, delete_type: DeleteType) -> DeleteBatch | None:
        preview = await self.preview(user, delete_type)
        if not preview.transactions:
            return None
        return await self.delete_transactions(user.id, preview.transactions, delete_type)

    async def delete_transactions(
        self, user_id: int, transactions: list[Transaction], delete_type: DeleteType
    ) -> DeleteBatch | None:
        own_transactions = [
            transaction
            for transaction in transactions
            if transaction.user_id == user_id and not transaction.is_deleted
        ]
        if not own_transactions:
            return None
        expires_at = utc_now() + timedelta(hours=settings.delete_undo_ttl_hours)
        batch = await self.batches.create(
            user_id=user_id,
            delete_type=delete_type,
            transactions=own_transactions,
            expires_at=expires_at,
        )
        for transaction in own_transactions:
            transaction.is_deleted = True
        await self.session.flush()
        return batch

    async def undo_last(self, user_id: int, batch_id: int | None = None) -> DeleteBatch | None:
        now = utc_now()
        batch = (
            await self.batches.get(batch_id, user_id)
            if batch_id is not None
            else await self.batches.get_last_restorable(user_id, now)
        )
        if batch is None or batch.restored_at is not None:
            return None
        if batch.expires_at is not None and batch.expires_at <= now:
            return None
        restored = 0
        for item in batch.items:
            transaction = item.transaction
            if transaction.user_id == user_id and transaction.is_deleted:
                transaction.is_deleted = False
                restored += 1
        batch.restored_at = now
        batch.transactions_count = restored or batch.transactions_count
        await self.session.flush()
        return batch
