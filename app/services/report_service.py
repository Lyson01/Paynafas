from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SalaryPeriod, Transaction, TransactionType, User
from app.repositories.no_spend_repository import NoSpendRepository
from app.repositories.salary_period_repository import SalaryPeriodRepository
from app.repositories.transaction_repository import TransactionRepository
from app.utils.dates import (
    current_day_bounds,
    current_month_bounds,
    current_week_bounds,
    format_date,
    format_time,
    get_zone,
    now_in_timezone,
)
from app.utils.money import format_money
from app.utils.text import html


@dataclass
class ReportData:
    title: str
    start: datetime | None
    end: datetime | None
    incomes: dict[str, Decimal]
    expenses: dict[str, Decimal]
    balance: dict[str, Decimal]
    category_expenses: dict[str, dict[str, Decimal]]
    transactions: list[Transaction]
    no_spend_days: int


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.transactions = TransactionRepository(session)
        self.periods = SalaryPeriodRepository(session)
        self.no_spend = NoSpendRepository(session)

    async def today(self, user: User) -> ReportData:
        start, end = current_day_bounds(user.settings.timezone)
        return await self._build(user, "Сегодня", start, end)

    async def week(self, user: User) -> ReportData:
        start, end = current_week_bounds(user.settings.timezone)
        return await self._build(user, "Неделя", start, end)

    async def month(self, user: User) -> ReportData:
        start, end = current_month_bounds(user.settings.timezone)
        return await self._build(user, "Месяц", start, end)

    async def alltime(self, user: User) -> ReportData:
        return await self._build(user, "Все время", None, None)

    async def salary_period(self, user: User) -> tuple[SalaryPeriod | None, ReportData | None]:
        period = await self.periods.get_active(user.id)
        if period is None:
            return None, None
        transactions = await self.transactions.list_for_period(user.id, period.id)
        data = self._from_transactions(
            user=user,
            title="Зарплатный период",
            start=period.start_datetime,
            end=period.expected_next_salary_datetime,
            transactions=transactions,
            no_spend_days=await self._count_no_spend(
                user.id,
                period.start_datetime.date(),
                (
                    period.expected_next_salary_datetime or now_in_timezone(user.settings.timezone)
                ).date(),
            ),
        )
        return period, data

    async def balance(self, user: User) -> tuple[SalaryPeriod | None, Decimal | None]:
        period = await self.periods.get_active(user.id)
        if period is None:
            return None, None
        transactions = await self.transactions.list_for_period(user.id, period.id)
        expenses = sum(
            Decimal(transaction.amount)
            for transaction in transactions
            if transaction.type == TransactionType.EXPENSE
            and transaction.currency == period.currency
        )
        return period, Decimal(period.salary_amount) - expenses

    async def history(self, user: User, limit: int = 10) -> list[Transaction]:
        return await self.transactions.list_between(
            user_id=user.id, start=None, end=None, limit=limit
        )

    async def _build(
        self, user: User, title: str, start: datetime | None, end: datetime | None
    ) -> ReportData:
        items = await self.transactions.list_between(user_id=user.id, start=start, end=end)
        no_spend_days = 0
        if start and end:
            no_spend_days = await self._count_no_spend(
                user.id, start.date(), (end - timedelta(days=1)).date()
            )
        return self._from_transactions(user, title, start, end, items, no_spend_days)

    def _from_transactions(
        self,
        user: User,
        title: str,
        start: datetime | None,
        end: datetime | None,
        transactions: list[Transaction],
        no_spend_days: int,
    ) -> ReportData:
        incomes: dict[str, Decimal] = defaultdict(Decimal)
        expenses: dict[str, Decimal] = defaultdict(Decimal)
        category_expenses: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        for item in transactions:
            amount = Decimal(item.amount)
            currency = item.currency
            if item.type == TransactionType.INCOME:
                incomes[currency] += amount
            else:
                expenses[currency] += amount
                category_expenses[item.category_name or "другое"][currency] += amount
        currencies = set(incomes) | set(expenses)
        balance = {currency: incomes[currency] - expenses[currency] for currency in currencies}
        return ReportData(
            title=title,
            start=start,
            end=end,
            incomes=dict(incomes),
            expenses=dict(expenses),
            balance=balance,
            category_expenses={k: dict(v) for k, v in category_expenses.items()},
            transactions=transactions,
            no_spend_days=no_spend_days,
        )

    async def _count_no_spend(self, user_id: int, start: date, end: date) -> int:
        if end < start:
            return 0
        return await self.no_spend.count_between(user_id, start, end)

    def render_basic_report(self, data: ReportData, timezone: str, *, premium: bool = True) -> str:
        period = self._period_title(data, timezone)
        lines = [f"📊 {data.title}", period, ""]
        lines.append(f"Доходы: {self._format_totals(data.incomes)}")
        lines.append(f"Расходы: {self._format_totals(data.expenses)}")
        lines.append(f"Баланс: {self._format_totals(data.balance)}")
        if data.start and data.end:
            days = max((data.end.date() - data.start.date()).days, 1)
            avg = self._average_expense(data.expenses, days)
            if avg:
                lines.append(f"Средний расход в день: {avg}")
        if data.category_expenses:
            lines.extend(["", "Топ категорий:"])
            for index, (name, totals) in enumerate(
                self._top_categories(data.category_expenses), start=1
            ):
                lines.append(f"{index}. {html(name.capitalize())} — {self._format_totals(totals)}")
        lines.append(f"Дней без трат: {data.no_spend_days}")
        if not premium:
            lines.extend(["", "Полная аналитика доступна в Premium."])
        return "\n".join(line for line in lines if line is not None)

    def render_period_report(
        self, period: SalaryPeriod, data: ReportData, timezone: str, *, premium: bool
    ) -> str:
        start = format_date(period.start_datetime, timezone)
        end = (
            format_date(period.expected_next_salary_datetime, timezone)
            if period.expected_next_salary_datetime
            else "не указана"
        )
        expenses_same_currency = data.expenses.get(period.currency, Decimal("0"))
        remaining = Decimal(period.salary_amount) - expenses_same_currency
        spent_percent = (
            (expenses_same_currency / Decimal(period.salary_amount) * Decimal("100"))
            if Decimal(period.salary_amount) > 0
            else Decimal("0")
        )
        lines = [
            f"Период: {start} — {end}",
            "",
            f"Зарплата: {format_money(period.salary_amount, period.currency)}",
            f"Доходы: {self._format_totals(data.incomes)}",
            f"Расходы: {self._format_totals(data.expenses)}",
            f"Осталось: {format_money(remaining, period.currency)}",
            "",
            f"Потрачено: {spent_percent.quantize(Decimal('0.1'))}%",
        ]
        if data.category_expenses:
            lines.extend(["", "Топ расходов:"])
            for index, (name, totals) in enumerate(
                self._top_categories(data.category_expenses), start=1
            ):
                lines.append(f"{index}. {html(name.capitalize())} — {self._format_totals(totals)}")

        days_elapsed = max(
            (now_in_timezone(timezone).date() - period.start_datetime.date()).days + 1, 1
        )
        average = expenses_same_currency / days_elapsed if days_elapsed else Decimal("0")
        if period.expected_next_salary_datetime:
            days_left = max(
                (
                    period.expected_next_salary_datetime.astimezone(get_zone(timezone)).date()
                    - now_in_timezone(timezone).date()
                ).days,
                0,
            )
            forecast_need = average * days_left
            lines.extend(
                [
                    "",
                    f"До следующей зарплаты: {days_left} дней",
                    f"Средний расход в день: {format_money(average, period.currency)}",
                    f"Дней без трат: {data.no_spend_days}",
                    "",
                    "Прогноз:",
                ]
            )
            if premium:
                if remaining >= forecast_need:
                    lines.append("Денег должно хватить.")
                else:
                    lines.append("При текущем темпе расходов денег может не хватить.")
                    shortage = forecast_need - remaining
                    lines.append(f"Примерно не хватает: {format_money(shortage, period.currency)}")
            else:
                lines.append("Подробный прогноз доступен в Premium.")
        return "\n".join(lines)

    def render_history(self, transactions: list[Transaction], timezone: str) -> str:
        if not transactions:
            return "История пока пустая."
        lines = ["Последние операции:"]
        for index, item in enumerate(transactions, start=1):
            sign = "+" if item.type == TransactionType.INCOME else "-"
            date_part = format_date(item.operation_datetime, timezone)
            time_part = format_time(item.operation_datetime, timezone)
            title = item.category_name or item.comment or "другое"
            lines.append(
                f"{index}. {date_part} {time_part} "
                f"{sign}{format_money(item.amount, item.currency)} — {html(title)}"
            )
        return "\n".join(lines)

    def _period_title(self, data: ReportData, timezone: str) -> str:
        if data.start and data.end:
            end = data.end - timedelta(seconds=1)
            return f"{format_date(data.start, timezone)} — {format_date(end, timezone)}"
        return "За все время"

    def _format_totals(self, totals: dict[str, Decimal]) -> str:
        if not totals:
            return "0"
        return ", ".join(format_money(amount, currency) for currency, amount in totals.items())

    def _top_categories(
        self, category_expenses: dict[str, dict[str, Decimal]], limit: int = 5
    ) -> list[tuple[str, dict[str, Decimal]]]:
        def total_in_first_currency(item: tuple[str, dict[str, Decimal]]) -> Decimal:
            return sum(item[1].values(), Decimal("0"))

        return sorted(category_expenses.items(), key=total_in_first_currency, reverse=True)[:limit]

    def _average_expense(self, expenses: dict[str, Decimal], days: int) -> str:
        if not expenses:
            return ""
        return ", ".join(
            format_money(amount / days, currency) for currency, amount in expenses.items()
        )
