from enum import StrEnum


class Plan(StrEnum):
    FREE = "free"
    PREMIUM = "premium"


class SalaryPeriodStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class TransactionType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class TransactionSource(StrEnum):
    TEXT = "text"
    MANUAL = "manual"
    ADMIN = "admin"
    IMPORT = "import"


class CategoryType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    BOTH = "both"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SubscriptionSource(StrEnum):
    PAYMENT = "payment"
    MANUAL = "manual"
    ADMIN = "admin"
    PROMO = "promo"


class BillingPeriod(StrEnum):
    MONTH = "month"
    YEAR = "year"
    MANUAL = "manual"
    PROMO = "promo"


class PaymentRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentProviderCode(StrEnum):
    MOCK = "mock"
    INTERNATIONAL_CARD = "international_card"
    UZBEK_CARD = "uzbek_card"


class PaymentMethod(StrEnum):
    VISA_MASTERCARD = "visa_mastercard"
    UZCARD_HUMO = "uzcard_humo"


class PaymentPlan(StrEnum):
    PREMIUM_MONTH = "premium_month"
    PREMIUM_YEAR = "premium_year"


class PaymentInvoiceStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class DeleteType(StrEnum):
    SINGLE = "single"
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    PERIOD = "period"
    ALL = "all"
    CUSTOM = "custom"
