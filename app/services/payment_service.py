from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BillingPeriod,
    PaymentInvoice,
    PaymentInvoiceStatus,
    PaymentMethod,
    PaymentPlan,
    PaymentProviderCode,
    SubscriptionSource,
    User,
)
from app.repositories.payment_invoice_repository import PaymentInvoiceRepository
from app.repositories.payment_webhook_repository import PaymentWebhookLogRepository
from app.repositories.user_repository import UserRepository
from app.services.payment_service_errors import PaymentUnavailableError
from app.services.payments.providers.base import PaymentProviderUnavailable
from app.services.payments.providers.factory import PaymentProviderFactory
from app.services.price_service import PriceService
from app.services.subscription_service import SubscriptionService
from app.utils.dates import utc_now


@dataclass(frozen=True)
class PaymentMethodOption:
    method: PaymentMethod
    title: str


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.invoices = PaymentInvoiceRepository(session)
        self.webhooks = PaymentWebhookLogRepository(session)
        self.providers = PaymentProviderFactory()
        self.prices = PriceService()

    def available_methods(self, user: User) -> list[PaymentMethodOption]:
        methods: list[PaymentMethodOption] = []
        if self.providers.is_method_available(PaymentMethod.VISA_MASTERCARD):
            methods.append(PaymentMethodOption(PaymentMethod.VISA_MASTERCARD, "Visa / Mastercard"))
        is_uz = user.settings.country_code == "UZ" or user.settings.default_currency == "UZS"
        if is_uz and self.providers.is_method_available(PaymentMethod.UZCARD_HUMO):
            methods.append(PaymentMethodOption(PaymentMethod.UZCARD_HUMO, "Uzcard / Humo"))
        return methods

    def price_for(self, user: User, plan: PaymentPlan) -> tuple[Decimal, str]:
        price = self.prices.get_price(user, plan)
        return price.amount, price.currency

    async def create_invoice(
        self, user: User, plan: PaymentPlan, method: PaymentMethod
    ) -> PaymentInvoice:
        if method not in {option.method for option in self.available_methods(user)}:
            raise PaymentUnavailableError("Payment method is temporarily unavailable")
        amount, currency = self.price_for(user, plan)
        provider = self.providers.provider_for_method(method)
        invoice = await self.invoices.create(
            user_id=user.id,
            provider=provider.code,
            payment_method=method,
            plan=plan,
            amount=amount,
            currency=currency,
            expires_at=utc_now() + timedelta(hours=1),
        )
        try:
            created = await provider.create_payment_link(invoice)
        except PaymentProviderUnavailable as exc:
            invoice.status = PaymentInvoiceStatus.FAILED
            await self.session.flush()
            raise PaymentUnavailableError(str(exc)) from exc
        invoice.provider_invoice_id = created.provider_invoice_id
        invoice.provider_payment_id = created.provider_payment_id
        invoice.payment_url = created.payment_url
        invoice.invoice_metadata = created.metadata
        await self.session.flush()
        return invoice

    async def cancel_invoice(self, user_id: int, invoice_id: int) -> PaymentInvoice | None:
        invoice = await self.invoices.get(invoice_id, user_id)
        if invoice is None or invoice.status != PaymentInvoiceStatus.PENDING:
            return invoice
        invoice.status = PaymentInvoiceStatus.CANCELLED
        await self.session.flush()
        return invoice

    async def check_invoice(self, user: User, invoice_id: int) -> PaymentInvoice | None:
        invoice = await self.invoices.get(invoice_id, user.id)
        if invoice is None:
            return None
        if invoice.status == PaymentInvoiceStatus.PENDING and invoice.expires_at:
            if invoice.expires_at <= utc_now():
                invoice.status = PaymentInvoiceStatus.EXPIRED
                await self.session.flush()
                return invoice
        provider = self.providers.provider_by_code(invoice.provider)
        try:
            status = await provider.get_payment_status(invoice)
        except PaymentProviderUnavailable:
            return invoice
        await self.apply_status(invoice, status.status, status.provider_payment_id)
        return invoice

    async def mock_mark_paid(self, invoice_id: int) -> PaymentInvoice | None:
        invoice = await self.invoices.get_for_update(invoice_id)
        if invoice is None:
            return None
        await self.apply_status(invoice, PaymentInvoiceStatus.PAID, f"mock-pay-{invoice.id}")
        return invoice

    async def process_webhook(
        self, provider_code: PaymentProviderCode, payload: dict[str, Any], headers: dict[str, str]
    ) -> PaymentInvoice | None:
        provider = self.providers.provider_by_code(provider_code)
        event = await provider.verify_webhook(payload, headers)
        log = await self.webhooks.create(
            provider=provider_code,
            event_id=event.event_id,
            event_type=event.event_type,
            payload=event.raw,
            signature_valid=event.signature_valid,
        )
        if not event.signature_valid:
            log.processing_error = "Invalid webhook signature"
            await self.session.flush()
            return None
        if event.event_id:
            existing = await self.webhooks.get_processed_event(provider_code, event.event_id)
            if existing and existing.id != log.id:
                log.processed = True
                await self.session.flush()
                return None

        invoice = None
        if event.invoice_id is not None:
            invoice = await self.invoices.get_for_update(event.invoice_id)
        if invoice is None and event.provider_invoice_id:
            invoice = await self.invoices.get_by_provider_invoice_id(event.provider_invoice_id)
        if invoice is None:
            log.processing_error = "Invoice not found"
            await self.session.flush()
            return None
        if event.status is not None:
            await self.apply_status(invoice, event.status, event.provider_payment_id)
        log.processed = True
        await self.session.flush()
        return invoice

    async def apply_status(
        self,
        invoice: PaymentInvoice,
        status: PaymentInvoiceStatus,
        provider_payment_id: str | None = None,
    ) -> None:
        if invoice.status == PaymentInvoiceStatus.PAID:
            return
        if status == PaymentInvoiceStatus.PAID:
            invoice.status = PaymentInvoiceStatus.PAID
            invoice.paid_at = utc_now()
            invoice.provider_payment_id = provider_payment_id or invoice.provider_payment_id
            user = await UserRepository(self.session).get_by_id(invoice.user_id)
            if user is not None:
                await SubscriptionService(self.session).activate_premium(
                    user,
                    days=self._duration_days(invoice.plan),
                    source=SubscriptionSource.PAYMENT,
                    billing_period=self._billing_period(invoice.plan),
                    payment_invoice_id=invoice.id,
                )
            return
        if status in {
            PaymentInvoiceStatus.FAILED,
            PaymentInvoiceStatus.EXPIRED,
            PaymentInvoiceStatus.CANCELLED,
            PaymentInvoiceStatus.REFUNDED,
        }:
            invoice.status = status
            invoice.provider_payment_id = provider_payment_id or invoice.provider_payment_id

    def _duration_days(self, plan: PaymentPlan) -> int:
        return 365 if plan == PaymentPlan.PREMIUM_YEAR else 30

    def _billing_period(self, plan: PaymentPlan) -> BillingPeriod:
        return BillingPeriod.YEAR if plan == PaymentPlan.PREMIUM_YEAR else BillingPeriod.MONTH
