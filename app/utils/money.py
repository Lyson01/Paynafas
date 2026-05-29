from decimal import ROUND_HALF_UP, Decimal

from app.utils.constants import CURRENCY_LABELS, CURRENCY_SYMBOLS


def normalize_amount(value: Decimal | int | float | str) -> Decimal:
    amount = Decimal(str(value))
    if amount == amount.to_integral():
        return amount.quantize(Decimal("1"))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_number(value: Decimal | int | float | str) -> str:
    amount = normalize_amount(value)
    if amount == amount.to_integral():
        return f"{int(amount):,}".replace(",", " ")
    return f"{amount:,.2f}".replace(",", " ").rstrip("0").rstrip(".")


def format_money(value: Decimal | int | float | str, currency: str) -> str:
    currency = (currency or "").upper()
    number = format_number(value)
    if currency == "UZS":
        return f"{number} сум"
    if currency in CURRENCY_SYMBOLS and currency != "USD":
        return f"{number} {CURRENCY_SYMBOLS[currency]}"
    if currency == "USD":
        return f"${number}" if Decimal(str(value)) < 1000 else f"{number} USD"
    label = CURRENCY_LABELS.get(currency, currency)
    return f"{number} {label}"


def sum_by_currency(items: list[tuple[Decimal, str]]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for amount, currency in items:
        key = currency.upper()
        totals[key] = totals.get(key, Decimal("0")) + Decimal(amount)
    return totals


def format_money_lines(values: dict[str, Decimal]) -> str:
    if not values:
        return "0"
    return "\n".join(f"- {format_money(amount, currency)}" for currency, amount in values.items())
