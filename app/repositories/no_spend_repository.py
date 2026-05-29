from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NoSpendDay


class NoSpendRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_get(self, *, user_id: int, day: date, timezone: str) -> NoSpendDay:
        dialect = self.session.bind.dialect.name if self.session.bind is not None else ""
        if dialect == "postgresql":
            stmt = (
                pg_insert(NoSpendDay)
                .values(user_id=user_id, date=day, timezone=timezone)
                .on_conflict_do_nothing(index_elements=["user_id", "date"])
            )
            await self.session.execute(stmt)
        existing = await self.get(user_id, day)
        if existing:
            return existing
        item = NoSpendDay(user_id=user_id, date=day, timezone=timezone)
        self.session.add(item)
        await self.session.flush()
        return item

    async def get(self, user_id: int, day: date) -> NoSpendDay | None:
        result = await self.session.execute(
            select(NoSpendDay).where(NoSpendDay.user_id == user_id, NoSpendDay.date == day)
        )
        return result.scalar_one_or_none()

    async def exists(self, user_id: int, day: date) -> bool:
        return await self.get(user_id, day) is not None

    async def delete_for_day(self, user_id: int, day: date) -> None:
        await self.session.execute(
            delete(NoSpendDay).where(NoSpendDay.user_id == user_id, NoSpendDay.date == day)
        )
        await self.session.flush()

    async def count_between(self, user_id: int, start: date, end: date) -> int:
        result = await self.session.execute(
            select(func.count(NoSpendDay.id)).where(
                NoSpendDay.user_id == user_id,
                NoSpendDay.date >= start,
                NoSpendDay.date <= end,
            )
        )
        return int(result.scalar_one() or 0)

    async def list_between(self, user_id: int, start: date, end: date) -> list[NoSpendDay]:
        result = await self.session.execute(
            select(NoSpendDay)
            .where(NoSpendDay.user_id == user_id, NoSpendDay.date >= start, NoSpendDay.date <= end)
            .order_by(NoSpendDay.date.asc())
        )
        return list(result.scalars())
