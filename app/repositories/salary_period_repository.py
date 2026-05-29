from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SalaryPeriod, SalaryPeriodStatus


class SalaryPeriodRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active(self, user_id: int) -> SalaryPeriod | None:
        result = await self.session.execute(
            select(SalaryPeriod)
            .where(
                SalaryPeriod.user_id == user_id,
                SalaryPeriod.status == SalaryPeriodStatus.ACTIVE,
            )
            .order_by(SalaryPeriod.start_datetime.desc())
        )
        return result.scalars().first()

    async def get_by_id(self, period_id: int) -> SalaryPeriod | None:
        result = await self.session.execute(
            select(SalaryPeriod).where(SalaryPeriod.id == period_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: int,
        salary_amount: Decimal,
        currency: str,
        start_datetime: datetime,
        expected_next_salary_datetime: datetime | None,
    ) -> SalaryPeriod:
        period = SalaryPeriod(
            user_id=user_id,
            salary_amount=salary_amount,
            currency=currency,
            start_datetime=start_datetime,
            expected_next_salary_datetime=expected_next_salary_datetime,
            status=SalaryPeriodStatus.ACTIVE,
        )
        self.session.add(period)
        await self.session.flush()
        return period

    async def close_active(
        self, user_id: int, actual_next_salary_datetime: datetime
    ) -> SalaryPeriod | None:
        result = await self.session.execute(
            select(SalaryPeriod)
            .where(
                SalaryPeriod.user_id == user_id,
                SalaryPeriod.status == SalaryPeriodStatus.ACTIVE,
            )
            .order_by(SalaryPeriod.start_datetime.desc())
        )
        periods = list(result.scalars())
        if not periods:
            return None
        for period in periods:
            period.status = SalaryPeriodStatus.CLOSED
            period.actual_next_salary_datetime = actual_next_salary_datetime
        await self.session.flush()
        return periods[0]

    async def list_active_with_expected_salary(self) -> list[SalaryPeriod]:
        result = await self.session.execute(
            select(SalaryPeriod).where(
                SalaryPeriod.status == SalaryPeriodStatus.ACTIVE,
                SalaryPeriod.expected_next_salary_datetime.is_not(None),
            )
        )
        return list(result.scalars())
