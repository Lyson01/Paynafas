from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TransactionSource, TransactionType
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.export_service import ExportService
from app.utils.dates import now_in_timezone


@pytest.mark.asyncio
async def test_export_csv_and_xlsx(session: AsyncSession) -> None:
    user, _ = await UserRepository(session).get_or_create(
        telegram_id=5001,
        username=None,
        first_name="A",
        last_name=None,
        language_code="ru",
    )
    await TransactionRepository(session).create(
        user_id=user.id,
        salary_period_id=None,
        type_=TransactionType.EXPENSE,
        amount=Decimal("25000"),
        currency="UZS",
        category_id=None,
        category_name="кафе",
        comment="кофе",
        operation_datetime=now_in_timezone(user.settings.timezone),
        source=TransactionSource.TEXT,
    )

    csv_content, csv_name = await ExportService(session).csv_file(user, "alltime")
    xlsx_content, xlsx_name = await ExportService(session).xlsx_file(user, "alltime")

    assert csv_name.endswith(".csv")
    assert "кофе".encode() in csv_content
    assert xlsx_name.endswith(".xlsx")
    assert xlsx_content.startswith(b"PK")
