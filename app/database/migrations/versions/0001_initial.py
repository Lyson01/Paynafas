"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-09 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.utils.constants import DEFAULT_CATEGORIES

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("language_code", sa.String(length=20), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "plan",
            sa.Enum("free", "premium", name="plan", native_enum=False),
            nullable=False,
            server_default="free",
        ),
        sa.Column("premium_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "registration_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "timezone", sa.String(length=100), nullable=False, server_default="Asia/Tashkent"
        ),
        sa.Column("default_currency", sa.String(length=10), nullable=False, server_default="UZS"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="ru"),
        sa.Column("locale", sa.String(length=50), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("country_name", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("date_format", sa.String(length=50), nullable=True),
        sa.Column("money_format", sa.String(length=50), nullable=True),
        sa.Column("next_salary_day", sa.Integer(), nullable=True),
        sa.Column(
            "daily_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "daily_reminder_time", sa.String(length=5), nullable=False, server_default="21:30"
        ),
        sa.Column(
            "report_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("raw_latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("raw_longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("user_id", name="uq_user_settings_user_id"),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column(
            "type",
            sa.Enum("income", "expense", "both", name="category_type", native_enum=False),
            nullable=False,
        ),
        sa.Column("emoji", sa.String(length=20), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("user_id", "slug", name="uq_categories_user_slug"),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"])

    op.create_table(
        "salary_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("salary_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="UZS"),
        sa.Column("start_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_next_salary_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_next_salary_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "closed", name="salary_period_status", native_enum=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_salary_periods_user_id", "salary_periods", ["user_id"])
    op.create_index("ix_salary_periods_status", "salary_periods", ["status"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "salary_period_id",
            sa.Integer(),
            sa.ForeignKey("salary_periods.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "type",
            sa.Enum("income", "expense", name="transaction_type", native_enum=False),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="UZS"),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category_name", sa.String(length=100), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("operation_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "source",
            sa.Enum(
                "text", "manual", "admin", "import", name="transaction_source", native_enum=False
            ),
            nullable=False,
            server_default="text",
        ),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_salary_period_id", "transactions", ["salary_period_id"])
    op.create_index("ix_transactions_type", "transactions", ["type"])
    op.create_index("ix_transactions_is_deleted", "transactions", ["is_deleted"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "plan",
            sa.Enum("free", "premium", name="subscription_plan", native_enum=False),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active", "expired", "cancelled", name="subscription_status", native_enum=False
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "source",
            sa.Enum("manual", "admin", "promo", name="subscription_source", native_enum=False),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    op.create_table(
        "payment_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "approved", "rejected", name="payment_request_status", native_enum=False
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("receipt_file_id", sa.String(length=255), nullable=True),
        sa.Column("admin_comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_payment_requests_user_id", "payment_requests", ["user_id"])
    op.create_index("ix_payment_requests_status", "payment_requests", ["status"])

    op.create_table(
        "no_spend_days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("user_id", "date", name="uq_no_spend_days_user_date"),
    )
    op.create_index("ix_no_spend_days_user_id", "no_spend_days", ["user_id"])
    op.create_index("ix_no_spend_days_date", "no_spend_days", ["date"])

    categories_table = sa.table(
        "categories",
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("type", sa.String),
        sa.column("emoji", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("user_id", sa.Integer),
    )
    op.bulk_insert(
        categories_table,
        [
            {
                "name": name,
                "slug": slug,
                "type": category_type,
                "emoji": emoji,
                "is_default": True,
                "user_id": None,
            }
            for slug, name, category_type, emoji in DEFAULT_CATEGORIES
        ],
    )


def downgrade() -> None:
    op.drop_table("no_spend_days")
    op.drop_table("payment_requests")
    op.drop_table("subscriptions")
    op.drop_table("transactions")
    op.drop_table("salary_periods")
    op.drop_table("categories")
    op.drop_table("user_settings")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
