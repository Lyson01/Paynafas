import csv
from io import BytesIO, StringIO

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, User
from app.repositories.salary_period_repository import SalaryPeriodRepository
from app.repositories.transaction_repository import TransactionRepository
from app.utils.dates import (
    current_day_bounds,
    current_month_bounds,
    current_week_bounds,
    format_date,
    format_time,
)


class ExportService:
    HEADERS = ["Дата", "Время", "Тип", "Сумма", "Валюта", "Категория", "Комментарий"]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.transactions = TransactionRepository(session)
        self.periods = SalaryPeriodRepository(session)

    async def collect(self, user: User, period: str) -> list[Transaction]:
        start = end = None
        if period == "today":
            start, end = current_day_bounds(user.settings.timezone)
        elif period == "week":
            start, end = current_week_bounds(user.settings.timezone)
        elif period == "month":
            start, end = current_month_bounds(user.settings.timezone)
        elif period == "salary":
            salary_period = await self.periods.get_active(user.id)
            if salary_period is None:
                return []
            return await self.transactions.list_for_period(user.id, salary_period.id)
        return await self.transactions.list_between(user_id=user.id, start=start, end=end)

    async def csv_file(self, user: User, period: str) -> tuple[bytes, str]:
        rows = await self.collect(user, period)
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(self.HEADERS)
        for row in rows:
            writer.writerow(self._row(row, user.settings.timezone))
        return output.getvalue().encode("utf-8-sig"), f"transactions_{period}.csv"

    async def xlsx_file(self, user: User, period: str) -> tuple[bytes, str]:
        rows = await self.collect(user, period)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Transactions"
        sheet.append(self.HEADERS)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in rows:
            sheet.append(self._row(row, user.settings.timezone))
        sheet.append([])
        sheet.append(["Итого операций", len(rows)])
        for column in sheet.columns:
            width = max(len(str(cell.value or "")) for cell in column) + 2
            sheet.column_dimensions[column[0].column_letter].width = min(width, 40)
        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue(), f"transactions_{period}.xlsx"

    def _row(self, transaction: Transaction, timezone: str) -> list[object]:
        return [
            format_date(transaction.operation_datetime, timezone),
            format_time(transaction.operation_datetime, timezone),
            transaction.type.value,
            float(transaction.amount),
            transaction.currency,
            transaction.category_name or "",
            transaction.comment or "",
        ]
