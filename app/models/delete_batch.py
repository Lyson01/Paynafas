from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import DeleteType

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class DeleteBatch(Base):
    __tablename__ = "delete_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    delete_type: Mapped[DeleteType] = mapped_column(
        Enum(DeleteType, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
    )
    transactions_count: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    items: Mapped[list["DeleteBatchItem"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class DeleteBatchItem(Base):
    __tablename__ = "delete_batch_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    delete_batch_id: Mapped[int] = mapped_column(
        ForeignKey("delete_batches.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), index=True
    )

    batch: Mapped[DeleteBatch] = relationship(back_populates="items")
    transaction: Mapped["Transaction"] = relationship()
