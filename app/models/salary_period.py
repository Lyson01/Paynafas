from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import SalaryPeriodStatus

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.user import User


class SalaryPeriod(Base):
    __tablename__ = "salary_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    salary_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="UZS")
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_next_salary_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_next_salary_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[SalaryPeriodStatus] = mapped_column(
        Enum(
            SalaryPeriodStatus,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
        ),
        default=SalaryPeriodStatus.ACTIVE,
        server_default=SalaryPeriodStatus.ACTIVE.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="salary_periods")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="salary_period")
