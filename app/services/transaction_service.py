from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, TransactionSource, TransactionType, User
from app.repositories.category_repository import CategoryRepository
from app.repositories.no_spend_repository import NoSpendRepository
from app.repositories.salary_period_repository import SalaryPeriodRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.parser_service import ParsedTransaction
from app.utils.dates import get_zone


@dataclass
class SaveTransactionResult:
    transaction: Transaction
    has_active_period: bool


class TransactionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.transactions = TransactionRepository(session)
        self.periods = SalaryPeriodRepository(session)
        self.categories = CategoryRepository(session)
        self.no_spend = NoSpendRepository(session)

    async def save_parsed(self, user: User, parsed: ParsedTransaction) -> SaveTransactionResult:
        active_period = await self.periods.get_active(user.id)
        category = None
        if parsed.category_slug:
            category = await self.categories.get_by_slug(parsed.category_slug, user.id)

        transaction = await self.transactions.create(
            user_id=user.id,
            salary_period_id=active_period.id if active_period else None,
            type_=parsed.type or TransactionType.EXPENSE,
            amount=Decimal(parsed.amount or 0),
            currency=parsed.currency or user.settings.default_currency,
            category_id=category.id if category else None,
            category_name=parsed.category_name,
            comment=parsed.comment,
            operation_datetime=parsed.operation_datetime,
            source=TransactionSource.TEXT,
            raw_text=parsed.raw_text,
        )
        if transaction.type == TransactionType.EXPENSE:
            local_day = transaction.operation_datetime.astimezone(
                get_zone(user.settings.timezone)
            ).date()
            await self.no_spend.delete_for_day(user.id, local_day)
        return SaveTransactionResult(
            transaction=transaction, has_active_period=active_period is not None
        )

    async def update_category(
        self, user_id: int, transaction_id: int, category_slug: str
    ) -> Transaction | None:
        category = await self.categories.get_by_slug(category_slug, user_id)
        if category is None:
            return None
        return await self.transactions.update_category(
            transaction_id, user_id, category.id, category.name
        )

    async def has_expense_on_day(
        self, user_id: int, day_start: datetime, day_end: datetime
    ) -> bool:
        return await self.transactions.has_expense_between(user_id, day_start, day_end)
