from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, TransactionSource, TransactionType


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        salary_period_id: int | None,
        type_: TransactionType,
        amount: Decimal,
        currency: str,
        category_id: int | None,
        category_name: str | None,
        comment: str | None,
        operation_datetime: datetime,
        source: TransactionSource = TransactionSource.TEXT,
        raw_text: str | None = None,
    ) -> Transaction:
        transaction = Transaction(
            user_id=user_id,
            salary_period_id=salary_period_id,
            type=type_,
            amount=amount,
            currency=currency.upper(),
            category_id=category_id,
            category_name=category_name,
            comment=comment,
            operation_datetime=operation_datetime,
            source=source,
            raw_text=raw_text,
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def get_by_id(
        self, transaction_id: int, user_id: int | None = None
    ) -> Transaction | None:
        query = select(Transaction).where(Transaction.id == transaction_id)
        if user_id is not None:
            query = query.where(Transaction.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_last(self, user_id: int) -> Transaction | None:
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id, Transaction.is_deleted.is_(False))
            .order_by(Transaction.operation_datetime.desc(), Transaction.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def soft_delete(self, transaction: Transaction) -> None:
        transaction.is_deleted = True
        await self.session.flush()

    async def restore(self, transaction: Transaction) -> None:
        transaction.is_deleted = False
        await self.session.flush()

    async def list_by_ids(self, user_id: int, transaction_ids: list[int]) -> list[Transaction]:
        if not transaction_ids:
            return []
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.id.in_(transaction_ids),
                Transaction.is_deleted.is_(False),
            )
        )
        return list(result.scalars())

    async def count_between(
        self,
        *,
        user_id: int,
        start: datetime | None,
        end: datetime | None,
        salary_period_id: int | None = None,
    ) -> int:
        query = select(func.count(Transaction.id)).where(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
        )
        if start is not None:
            query = query.where(Transaction.operation_datetime >= start)
        if end is not None:
            query = query.where(Transaction.operation_datetime < end)
        if salary_period_id is not None:
            query = query.where(Transaction.salary_period_id == salary_period_id)
        result = await self.session.execute(query)
        return int(result.scalar_one() or 0)

    async def update_category(
        self, transaction_id: int, user_id: int, category_id: int | None, category_name: str
    ) -> Transaction | None:
        transaction = await self.get_by_id(transaction_id, user_id)
        if transaction is None:
            return None
        transaction.category_id = category_id
        transaction.category_name = category_name
        await self.session.flush()
        return transaction

    async def list_between(
        self,
        *,
        user_id: int,
        start: datetime | None,
        end: datetime | None,
        limit: int | None = None,
    ) -> list[Transaction]:
        query = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
        )
        if start is not None:
            query = query.where(Transaction.operation_datetime >= start)
        if end is not None:
            query = query.where(Transaction.operation_datetime < end)
        query = query.order_by(Transaction.operation_datetime.desc(), Transaction.id.desc())
        if limit:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars())

    async def list_for_period(self, user_id: int, salary_period_id: int) -> list[Transaction]:
        result = await self.session.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.salary_period_id == salary_period_id,
                Transaction.is_deleted.is_(False),
            )
            .order_by(Transaction.operation_datetime.asc())
        )
        return list(result.scalars())

    async def count_for_month(self, user_id: int, start: datetime, end: datetime) -> int:
        result = await self.session.execute(
            select(func.count(Transaction.id)).where(
                Transaction.user_id == user_id,
                Transaction.created_at >= start,
                Transaction.created_at < end,
                Transaction.is_deleted.is_(False),
            )
        )
        return int(result.scalar_one())

    async def has_expense_between(self, user_id: int, start: datetime, end: datetime) -> bool:
        result = await self.session.execute(
            select(Transaction.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.operation_datetime >= start,
                Transaction.operation_datetime < end,
                Transaction.is_deleted.is_(False),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def count_expense_days(self, user_id: int, start: datetime, end: datetime) -> int:
        day_expr = func.date(Transaction.operation_datetime)
        result = await self.session.execute(
            select(func.count(func.distinct(day_expr))).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.operation_datetime >= start,
                Transaction.operation_datetime < end,
                Transaction.is_deleted.is_(False),
            )
        )
        return int(result.scalar_one() or 0)

    async def monthly_operation_count(self, user_id: int, day: date) -> int:
        start = datetime(day.year, day.month, 1)
        end = datetime(day.year + (day.month // 12), (day.month % 12) + 1, 1)
        return await self.count_for_month(user_id, start, end)

    async def totals_between(
        self, user_id: int, start: datetime | None, end: datetime | None
    ) -> list[tuple[str, str, Decimal]]:
        query = (
            select(
                Transaction.type,
                Transaction.currency,
                func.coalesce(func.sum(Transaction.amount), 0),
            )
            .where(Transaction.user_id == user_id, Transaction.is_deleted.is_(False))
            .group_by(Transaction.type, Transaction.currency)
        )
        if start is not None:
            query = query.where(Transaction.operation_datetime >= start)
        if end is not None:
            query = query.where(Transaction.operation_datetime < end)
        result = await self.session.execute(query)
        return [(str(row[0]), str(row[1]), Decimal(row[2])) for row in result.all()]

    async def admin_counts(self, today_start: datetime, month_start: datetime) -> tuple[int, int]:
        result = await self.session.execute(
            select(
                func.sum(case((Transaction.created_at >= today_start, 1), else_=0)),
                func.sum(case((Transaction.created_at >= month_start, 1), else_=0)),
            ).where(Transaction.is_deleted.is_(False))
        )
        row = result.one()
        return int(row[0] or 0), int(row[1] or 0)
