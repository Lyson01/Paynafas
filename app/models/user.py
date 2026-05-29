from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import Plan

if TYPE_CHECKING:
    from app.models.salary_period import SalaryPeriod
    from app.models.transaction import Transaction
    from app.models.user_settings import UserSettings


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(20))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    plan: Mapped[Plan] = mapped_column(
        Enum(Plan, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=Plan.FREE,
        server_default=Plan.FREE.value,
    )
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    settings: Mapped[UserSettings] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    transactions: Mapped[list[Transaction]] = relationship(back_populates="user")
    salary_periods: Mapped[list[SalaryPeriod]] = relationship(back_populates="user")
