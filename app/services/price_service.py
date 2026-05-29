from dataclasses import dataclass
from decimal import Decimal

from app.config import settings
from app.models import PaymentPlan, User


@dataclass(frozen=True)
class Price:
    amount: Decimal
    currency: str


class PriceService:
    def get_price(self, user: User, plan: PaymentPlan) -> Price:
        is_uz = (
            user.settings.country_code == "UZ" or user.settings.default_currency.upper() == "UZS"
        )
        if is_uz:
            amount = (
                Decimal(settings.premium_monthly_price_uzs)
                if plan == PaymentPlan.PREMIUM_MONTH
                else Decimal(settings.premium_yearly_price_uzs)
            )
            return Price(amount=amount, currency="UZS")
        amount = (
            Decimal(str(settings.premium_monthly_price_usd))
            if plan == PaymentPlan.PREMIUM_MONTH
            else Decimal(str(settings.premium_yearly_price_usd))
        )
        return Price(amount=amount, currency="USD")
