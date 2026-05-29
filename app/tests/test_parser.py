from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.models import TransactionType
from app.services.parser_service import ParserService


def fixed_now() -> datetime:
    return datetime(2026, 5, 9, 10, 15, tzinfo=ZoneInfo("Asia/Tashkent"))


def test_parse_basic_expense_amount_category() -> None:
    parsed = ParserService().parse("кофе 25000", now=fixed_now())

    assert parsed.amount == Decimal("25000")
    assert parsed.currency == "UZS"
    assert parsed.type == TransactionType.EXPENSE
    assert parsed.category_slug == "cafe"
    assert parsed.operation_datetime.date().isoformat() == "2026-05-09"


def test_parse_income_salary_million() -> None:
    parsed = ParserService().parse("получил зп 5 млн", now=fixed_now())

    assert parsed.amount == Decimal("5000000")
    assert parsed.type == TransactionType.INCOME
    assert parsed.is_salary_related is True
    assert parsed.category_slug == "salary"


def test_parse_currency_usd() -> None:
    parsed = ParserService().parse("аренда 300$", now=fixed_now())

    assert parsed.amount == Decimal("300")
    assert parsed.currency == "USD"


def test_parse_relative_date_and_time() -> None:
    parsed = ParserService().parse("вчера в 21:30 аптека 70000", now=fixed_now())

    assert parsed.operation_datetime.date().isoformat() == "2026-05-08"
    assert parsed.operation_datetime.strftime("%H:%M") == "21:30"
    assert parsed.category_slug == "health"


def test_parse_absolute_date_defaults_to_noon() -> None:
    parsed = ParserService().parse("05.05.2026 обед 45000", now=fixed_now())

    assert parsed.operation_datetime.date().isoformat() == "2026-05-05"
    assert parsed.operation_datetime.strftime("%H:%M") == "12:00"
    assert parsed.amount == Decimal("45000")
