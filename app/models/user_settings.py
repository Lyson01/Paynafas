from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    registration_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    timezone: Mapped[str] = mapped_column(String(100), default="Asia/Tashkent")
    default_currency: Mapped[str] = mapped_column(String(10), default="UZS")
    language: Mapped[str] = mapped_column(String(10), default="ru")
    locale: Mapped[str | None] = mapped_column(String(50))
    country_code: Mapped[str | None] = mapped_column(String(2))
    country_name: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(255))
    date_format: Mapped[str | None] = mapped_column(String(50))
    money_format: Mapped[str | None] = mapped_column(String(50))
    next_salary_day: Mapped[int | None] = mapped_column()
    daily_reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    daily_reminder_time: Mapped[str] = mapped_column(String(5), default="21:30")
    report_reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    raw_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    raw_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="settings")
