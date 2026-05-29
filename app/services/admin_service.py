from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaymentRequestStatus, SubscriptionSource
from app.repositories.payment_repository import PaymentRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService
from app.utils.dates import current_day_bounds, current_month_bounds, utc_now


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.payments = PaymentRepository(session)
        self.transactions = TransactionRepository(session)
        self.subscriptions = SubscriptionService(session)

    async def stats(self) -> str:
        now = utc_now()
        total_users = await self.users.count_users()
        dau = await self.users.count_active_since(now - timedelta(days=1))
        mau = await self.users.count_active_since(now - timedelta(days=30))
        today_start, _ = current_day_bounds("UTC")
        month_start, _ = current_month_bounds("UTC")
        today_ops, month_ops = await self.transactions.admin_counts(today_start, month_start)
        return (
            "Админ-статистика:\n"
            f"Пользователей: {total_users}\n"
            f"DAU: {dau}\n"
            f"MAU: {mau}\n"
            f"Операций сегодня: {today_ops}\n"
            f"Операций за месяц: {month_ops}"
        )

    async def approve_payment(self, request_id: int, days: int = 30) -> int | None:
        request = await self.payments.get(request_id)
        if request is None:
            return None
        if request.status != PaymentRequestStatus.PENDING:
            return None
        user = await self.users.get_by_id(request.user_id)
        if user is None:
            return None
        await self.payments.set_status(request, PaymentRequestStatus.APPROVED)
        await self.subscriptions.activate_premium(user, days=days, source=SubscriptionSource.ADMIN)
        return user.telegram_id

    async def reject_payment(self, request_id: int, comment: str | None = None) -> int | None:
        request = await self.payments.get(request_id)
        if request is None:
            return None
        if request.status != PaymentRequestStatus.PENDING:
            return None
        user = await self.users.get_by_id(request.user_id)
        await self.payments.set_status(request, PaymentRequestStatus.REJECTED, comment)
        return user.telegram_id if user else None

    async def grant_premium(self, telegram_id: int, days: int) -> bool:
        user = await self.users.get_by_telegram_id(telegram_id)
        if user is None:
            return False
        await self.subscriptions.activate_premium(user, days=days, source=SubscriptionSource.ADMIN)
        return True

    async def revoke_premium(self, telegram_id: int) -> bool:
        user = await self.users.get_by_telegram_id(telegram_id)
        if user is None:
            return False
        try:
            await self.subscriptions.revoke_premium(user)
        except ValueError:
            return False
        return True
