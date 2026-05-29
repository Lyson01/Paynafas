from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import TransactionSource, TransactionType

if TYPE_CHECKING:
    from app.models.salary_period import SalaryPeriod
    from app.models.user import User


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    salary_period_id: Mapped[int | None] = mapped_column(
        ForeignKey("salary_periods.id", ondelete="SET NULL"), index=True
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="UZS")
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    category_name: Mapped[str | None] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(Text)
    operation_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    source: Mapped[TransactionSource] = mapped_column(
        Enum(
            TransactionSource,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
        ),
        default=TransactionSource.TEXT,
        server_default=TransactionSource.TEXT.value,
    )
    raw_text: Mapped[str | None] = mapped_column(Text)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", index=True
    )

    user: Mapped[User] = relationship(back_populates="transactions")
    salary_period: Mapped[SalaryPeriod | None] = relationship(back_populates="transactions")
