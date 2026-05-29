import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from app.models import TransactionType
from app.utils.dates import get_zone, now_in_timezone
from app.utils.text import clean_spaces


@dataclass
class ParsedTransaction:
    type: TransactionType | None
    amount: Decimal | None
    currency: str | None
    category_slug: str | None
    category_name: str | None
    comment: str | None
    operation_datetime: datetime
    is_salary_related: bool
    confidence: float
    raw_text: str


class ParserService:
    CURRENCY_ALIASES = {
        "$": "USD",
        "usd": "USD",
        "доллар": "USD",
        "долларов": "USD",
        "сум": "UZS",
        "сумов": "UZS",
        "som": "UZS",
        "so'm": "UZS",
        "uzs": "UZS",
        "руб": "RUB",
        "рублей": "RUB",
        "rub": "RUB",
        "₽": "RUB",
        "kzt": "KZT",
        "тенге": "KZT",
        "₸": "KZT",
        "eur": "EUR",
        "€": "EUR",
        "gbp": "GBP",
        "£": "GBP",
        "try": "TRY",
        "aed": "AED",
    }
    CURRENCY_RE = (
        r"\$|€|₽|₸|£|usd|uzs|rub|kzt|eur|gbp|try|aed|"
        r"сум(?:ов)?|so'?m|som|руб(?:лей)?|тенге|доллар(?:ов)?"
    )
    MULTIPLIERS = {
        "млн": Decimal("1000000"),
        "миллион": Decimal("1000000"),
        "миллиона": Decimal("1000000"),
        "миллионов": Decimal("1000000"),
        "m": Decimal("1000000"),
        "к": Decimal("1000"),
        "k": Decimal("1000"),
        "тыс": Decimal("1000"),
    }
    INCOME_KEYWORDS = {
        "зарплата",
        "зп",
        "получил",
        "получила",
        "доход",
        "аванс",
        "премия",
        "перевод получил",
        "вернули долг",
        "salary",
        "income",
        "bonus",
        "oylik",
        "daromad",
    }
    SALARY_KEYWORDS = {"зарплата", "зп", "аванс", "salary", "oylik"}
    CATEGORY_KEYWORDS = {
        "cafe": {"кофе", "кафе", "чай", "обед", "ужин", "плов", "бургер", "ресторан", "coffee"},
        "groceries": {"продукты", "базар", "супермаркет", "корзинка", "makro", "market"},
        "transport": {"такси", "yandex", "яндекс", "автобус", "метро", "бензин", "taxi"},
        "health": {"аптека", "лекарства", "врач", "клиника", "doctor", "pharmacy"},
        "rent": {"аренда", "квартира", "комната", "rent"},
        "internet": {"интернет", "wifi", "вайфай", "провайдер"},
        "mobile": {"ucell", "beeline", "uzmobile", "mobiuz", "связь"},
        "subscriptions": {"netflix", "spotify", "youtube", "telegram premium", "подписка"},
        "education": {"курс", "обучение", "книга", "учеба"},
        "clothes": {"одежда", "обувь", "футболка"},
        "entertainment": {"кино", "игра", "развлечения"},
        "salary": {"зарплата", "зп", "salary", "oylik"},
        "advance": {"аванс"},
        "bonus": {"премия", "bonus"},
        "debt_return": {"вернули долг", "возврат долга"},
    }
    CATEGORY_NAMES = {
        "cafe": "кафе",
        "food": "еда",
        "groceries": "продукты",
        "transport": "транспорт",
        "health": "здоровье",
        "rent": "аренда",
        "internet": "интернет",
        "mobile": "связь",
        "subscriptions": "подписки",
        "education": "обучение",
        "clothes": "одежда",
        "entertainment": "развлечения",
        "salary": "зарплата",
        "advance": "аванс",
        "bonus": "премия",
        "debt_return": "возврат долга",
        "other_expense": "другое",
        "other_income": "другое",
    }
    MONTHS = {
        "января": 1,
        "январь": 1,
        "февраля": 2,
        "февраль": 2,
        "марта": 3,
        "март": 3,
        "апреля": 4,
        "апрель": 4,
        "мая": 5,
        "май": 5,
        "июня": 6,
        "июнь": 6,
        "июля": 7,
        "июль": 7,
        "августа": 8,
        "август": 8,
        "сентября": 9,
        "сентябрь": 9,
        "октября": 10,
        "октябрь": 10,
        "ноября": 11,
        "ноябрь": 11,
        "декабря": 12,
        "декабрь": 12,
        "june": 6,
        "iyun": 6,
        "may": 5,
    }

    AMOUNT_RE = re.compile(
        rf"(?P<prefix>{CURRENCY_RE})?\s*(?P<sign>[+-])?\s*"
        r"(?P<number>\d+(?:[\s.,]\d+)*)\s*"
        r"(?P<mult>млн|миллион(?:а|ов)?|тыс|[kкm])?\s*"
        rf"(?P<currency>{CURRENCY_RE})?",
        re.IGNORECASE,
    )
    DATE_NUMERIC_RE = re.compile(
        r"\b(?P<day>\d{1,2})[.\/-](?P<month>\d{1,2})" r"(?:[.\/-](?P<year>\d{2,4}))?\b"
    )
    TIME_RE = re.compile(
        r"\b(?:в\s*)?(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)\b",
        re.IGNORECASE,
    )
    MONTH_TEXT_RE = re.compile(
        r"\b(?P<day>\d{1,2})\s+(?P<month>"
        + "|".join(sorted(MONTHS, key=len, reverse=True))
        + r")(?:\s+(?P<year>\d{4}))?\b",
        re.IGNORECASE,
    )

    def parse(
        self,
        text: str,
        *,
        default_currency: str = "UZS",
        timezone: str = "Asia/Tashkent",
        now: datetime | None = None,
    ) -> ParsedTransaction:
        raw_text = clean_spaces(text)
        local_now = now.astimezone(get_zone(timezone)) if now else now_in_timezone(timezone)
        lower = raw_text.lower().replace("ё", "е")

        operation_datetime, date_time_spans, explicit_date, explicit_time = self._parse_datetime(
            lower, timezone, local_now
        )
        amount, currency, amount_spans = self._parse_amount(
            lower, default_currency, date_time_spans
        )
        type_ = self._detect_type(lower, amount)
        is_salary_related = any(keyword in lower for keyword in self.SALARY_KEYWORDS)
        category_slug = self._detect_category(lower, type_)
        category_name = self.CATEGORY_NAMES.get(category_slug or "")
        comment = self._build_comment(raw_text, [*date_time_spans, *amount_spans])
        confidence = 0.92 if amount is not None else 0.0
        if explicit_date or explicit_time:
            confidence += 0.03
        if category_slug:
            confidence += 0.03

        return ParsedTransaction(
            type=type_,
            amount=amount,
            currency=currency,
            category_slug=category_slug,
            category_name=category_name,
            comment=comment,
            operation_datetime=operation_datetime,
            is_salary_related=is_salary_related,
            confidence=min(confidence, 0.99),
            raw_text=raw_text,
        )

    def parse_next_salary_date(
        self, text: str, *, base_datetime: datetime, timezone: str
    ) -> datetime | None:
        lower = clean_spaces(text).lower()
        zone = get_zone(timezone)
        base = base_datetime.astimezone(zone)
        if lower in {"пропустить", "skip", "нет", "yoq", "o'tkazib yuborish"}:
            return None
        if "через месяц" in lower or "in a month" in lower or "bir oy" in lower:
            month = base.month + 1
            year = base.year + month // 13
            month = ((month - 1) % 12) + 1
            day = min(base.day, self._last_day_of_month(year, month))
            return datetime(year, month, day, base.hour, base.minute, tzinfo=zone)

        day_of_month = re.search(r"\b(?P<day>\d{1,2})\s*(?:числа|-?kuni)?\b", lower)
        if day_of_month:
            day = int(day_of_month.group("day"))
            month = base.month
            year = base.year
            if day <= base.day:
                month += 1
                if month == 13:
                    month = 1
                    year += 1
            day = min(day, self._last_day_of_month(year, month))
            return datetime(year, month, day, 12, 0, tzinfo=zone)

        parsed, _, explicit_date, _ = self._parse_datetime(lower, timezone, base)
        return parsed if explicit_date else None

    def _parse_datetime(
        self, text: str, timezone: str, local_now: datetime
    ) -> tuple[datetime, list[tuple[int, int]], bool, bool]:
        spans: list[tuple[int, int]] = []
        zone = get_zone(timezone)
        selected_date = local_now.date()
        selected_time = time(local_now.hour, local_now.minute)
        explicit_date = False
        explicit_time = False
        date_without_time = False

        if match := self.DATE_NUMERIC_RE.search(text):
            day = int(match.group("day"))
            month = int(match.group("month"))
            year_text = match.group("year")
            year = int(year_text) if year_text else local_now.year
            if year < 100:
                year += 2000
            selected_date = date(year, month, day)
            spans.append(match.span())
            explicit_date = True
            date_without_time = True
        elif match := self.MONTH_TEXT_RE.search(text):
            day = int(match.group("day"))
            month = self.MONTHS[match.group("month").lower()]
            year = int(match.group("year")) if match.group("year") else local_now.year
            selected_date = date(year, month, day)
            spans.append(match.span())
            explicit_date = True
            date_without_time = True
        elif "вчера" in text or "yesterday" in text or "kecha" in text:
            selected_date = local_now.date() - timedelta(days=1)
            for word in ("вчера", "yesterday", "kecha"):
                index = text.find(word)
                if index >= 0:
                    spans.append((index, index + len(word)))
            explicit_date = True
        elif "сегодня" in text or "today" in text or "bugun" in text:
            selected_date = local_now.date()
            for word in ("сегодня", "today", "bugun"):
                index = text.find(word)
                if index >= 0:
                    spans.append((index, index + len(word)))
            explicit_date = True

        if match := self.TIME_RE.search(text):
            selected_time = time(int(match.group("hour")), int(match.group("minute")))
            spans.append(match.span())
            explicit_time = True
        elif date_without_time:
            selected_time = time(12, 0)

        return (
            datetime.combine(selected_date, selected_time, zone),
            spans,
            explicit_date,
            explicit_time,
        )

    def _parse_amount(
        self,
        text: str,
        default_currency: str,
        blocked_spans: list[tuple[int, int]],
    ) -> tuple[Decimal | None, str | None, list[tuple[int, int]]]:
        candidates: list[tuple[Decimal, str, tuple[int, int]]] = []
        for match in self.AMOUNT_RE.finditer(text):
            if not match.group("number"):
                continue
            if self._overlaps(match.span(), blocked_spans):
                continue
            try:
                amount = self._normalize_number(match.group("number"), match.group("mult"))
            except InvalidOperation:
                continue
            if amount <= 0:
                continue
            currency_token = match.group("currency") or match.group("prefix")
            currency = self._normalize_currency(currency_token) or default_currency.upper()
            candidates.append((amount, currency, match.span()))

        if not candidates:
            return None, None, []
        amount, currency, span = candidates[-1]
        return amount, currency, [span]

    def _normalize_number(self, number: str, multiplier_token: str | None) -> Decimal:
        value = number.replace(" ", "")
        multiplier = self.MULTIPLIERS.get((multiplier_token or "").lower(), Decimal("1"))
        if multiplier != 1:
            value = value.replace(",", ".")
            return Decimal(value) * multiplier
        separators = [char for char in value if char in ".,"]
        if not separators:
            return Decimal(value)
        if len(set(separators)) == 1:
            separator = separators[0]
            parts = value.split(separator)
            if len(parts[-1]) == 3 and all(len(part) == 3 for part in parts[1:]):
                return Decimal("".join(parts))
            return Decimal(value.replace(",", "."))
        cleaned = value.replace(".", "").replace(",", "")
        return Decimal(cleaned)

    def _normalize_currency(self, token: str | None) -> str | None:
        if not token:
            return None
        return self.CURRENCY_ALIASES.get(token.lower())

    def _detect_type(self, text: str, amount: Decimal | None) -> TransactionType | None:
        if amount is None:
            return None
        if any(keyword in text for keyword in self.INCOME_KEYWORDS):
            return TransactionType.INCOME
        return TransactionType.EXPENSE

    def _detect_category(self, text: str, type_: TransactionType | None) -> str | None:
        for slug, keywords in self.CATEGORY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return slug
        if type_ == TransactionType.INCOME:
            return "other_income"
        if type_ == TransactionType.EXPENSE:
            return "other_expense"
        return None

    def _build_comment(self, raw_text: str, spans: list[tuple[int, int]]) -> str | None:
        chars = list(raw_text)
        for start, end in spans:
            for index in range(start, min(end, len(chars))):
                chars[index] = " "
        comment = clean_spaces("".join(chars).strip(" -—:,"))
        return comment or None

    def _overlaps(self, span: tuple[int, int], blocked_spans: list[tuple[int, int]]) -> bool:
        start, end = span
        return any(
            start < blocked_end and end > blocked_start
            for blocked_start, blocked_end in blocked_spans
        )

    def _last_day_of_month(self, year: int, month: int) -> int:
        if month == 12:
            return 31
        return (date(year, month + 1, 1) - timedelta(days=1)).day
