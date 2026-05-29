from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SalaryPeriod, Transaction
from app.repositories.salary_period_repository import SalaryPeriodRepository


class SalaryPeriodService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.periods = SalaryPeriodRepository(session)

    async def get_active(self, user_id: int) -> SalaryPeriod | None:
        return await self.periods.get_active(user_id)

    async def create_from_income(
        self, transaction: Transaction, expected_next_salary_datetime: datetime | None = None
    ) -> SalaryPeriod:
        await self.periods.close_active(transaction.user_id, transaction.operation_datetime)
        period = await self.periods.create(
            user_id=transaction.user_id,
            salary_amount=Decimal(transaction.amount),
            currency=transaction.currency,
            start_datetime=transaction.operation_datetime,
            expected_next_salary_datetime=expected_next_salary_datetime,
        )
        transaction.salary_period_id = period.id
        await self.session.flush()
        return period

    async def close_current(self, user_id: int, closed_at: datetime) -> SalaryPeriod | None:
        return await self.periods.close_active(user_id, closed_at)
