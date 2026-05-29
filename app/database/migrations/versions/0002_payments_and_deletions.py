"""payments and delete batches

Revision ID: 0002_payments_and_deletions
Revises: 0001_initial
Create Date: 2026-05-09 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_payments_and_deletions"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscription_source")
        op.execute("ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_source_check")
        op.execute(
            "ALTER TABLE subscriptions ADD CONSTRAINT subscription_source "
            "CHECK (source IN ('payment', 'manual', 'admin', 'promo'))"
        )

    op.create_table(
        "payment_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "provider",
            sa.Enum(
                "mock",
                "international_card",
                "uzbek_card",
                name="payment_provider_code",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "payment_method",
            sa.Enum(
                "visa_mastercard",
                "uzcard_humo",
                name="payment_method",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "plan",
            sa.Enum(
                "premium_month",
                "premium_year",
                name="payment_plan",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "paid",
                "failed",
                "expired",
                "cancelled",
                "refunded",
                name="payment_invoice_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("provider_invoice_id", sa.String(length=255), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=True),
        sa.Column("payment_url", sa.String(length=2048), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_payment_invoices_user_id", "payment_invoices", ["user_id"])
    op.create_index("ix_payment_invoices_provider", "payment_invoices", ["provider"])
    op.create_index("ix_payment_invoices_status", "payment_invoices", ["status"])
    op.create_index("ix_payment_invoices_expires_at", "payment_invoices", ["expires_at"])
    op.create_index(
        "uq_payment_invoices_provider_invoice_id",
        "payment_invoices",
        ["provider_invoice_id"],
        unique=True,
    )

    op.add_column(
        "subscriptions",
        sa.Column(
            "billing_period",
            sa.Enum("month", "year", "manual", "promo", name="billing_period", native_enum=False),
            nullable=False,
            server_default="manual",
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "payment_invoice_id",
            sa.Integer(),
            sa.ForeignKey("payment_invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_subscriptions_payment_invoice_id",
        "subscriptions",
        ["payment_invoice_id"],
    )

    op.create_table(
        "payment_webhook_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "provider",
            sa.Enum(
                "mock",
                "international_card",
                "uzbek_card",
                name="payment_webhook_provider",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("event_id", sa.String(length=255), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("signature_valid", sa.Boolean(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_payment_webhook_logs_provider", "payment_webhook_logs", ["provider"])
    op.create_index("ix_payment_webhook_logs_event_id", "payment_webhook_logs", ["event_id"])
    op.create_index("ix_payment_webhook_logs_processed", "payment_webhook_logs", ["processed"])

    op.create_table(
        "delete_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "delete_type",
            sa.Enum(
                "single",
                "today",
                "week",
                "month",
                "period",
                "all",
                "custom",
                name="delete_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("transactions_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_delete_batches_user_id", "delete_batches", ["user_id"])
    op.create_index("ix_delete_batches_expires_at", "delete_batches", ["expires_at"])
    op.create_index("ix_delete_batches_restored_at", "delete_batches", ["restored_at"])

    op.create_table(
        "delete_batch_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "delete_batch_id",
            sa.Integer(),
            sa.ForeignKey("delete_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.Integer(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_delete_batch_items_delete_batch_id",
        "delete_batch_items",
        ["delete_batch_id"],
    )
    op.create_index(
        "ix_delete_batch_items_transaction_id",
        "delete_batch_items",
        ["transaction_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_delete_batch_items_transaction_id", table_name="delete_batch_items")
    op.drop_index("ix_delete_batch_items_delete_batch_id", table_name="delete_batch_items")
    op.drop_table("delete_batch_items")
    op.drop_index("ix_delete_batches_restored_at", table_name="delete_batches")
    op.drop_index("ix_delete_batches_expires_at", table_name="delete_batches")
    op.drop_index("ix_delete_batches_user_id", table_name="delete_batches")
    op.drop_table("delete_batches")

    op.drop_index("ix_payment_webhook_logs_processed", table_name="payment_webhook_logs")
    op.drop_index("ix_payment_webhook_logs_event_id", table_name="payment_webhook_logs")
    op.drop_index("ix_payment_webhook_logs_provider", table_name="payment_webhook_logs")
    op.drop_table("payment_webhook_logs")

    op.drop_index("ix_subscriptions_payment_invoice_id", table_name="subscriptions")
    op.drop_column("subscriptions", "payment_invoice_id")
    op.drop_column("subscriptions", "billing_period")

    op.drop_index("uq_payment_invoices_provider_invoice_id", table_name="payment_invoices")
    op.drop_index("ix_payment_invoices_expires_at", table_name="payment_invoices")
    op.drop_index("ix_payment_invoices_status", table_name="payment_invoices")
    op.drop_index("ix_payment_invoices_provider", table_name="payment_invoices")
    op.drop_index("ix_payment_invoices_user_id", table_name="payment_invoices")
    op.drop_table("payment_invoices")

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscription_source")
        op.execute(
            "ALTER TABLE subscriptions ADD CONSTRAINT subscription_source "
            "CHECK (source IN ('manual', 'admin', 'promo'))"
        )
