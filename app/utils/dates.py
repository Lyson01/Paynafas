from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def get_zone(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone)
    except Exception:
        return ZoneInfo("Asia/Tashkent")


def utc_now() -> datetime:
    return datetime.now(UTC)


def now_in_timezone(timezone: str) -> datetime:
    return utc_now().astimezone(get_zone(timezone))


def local_day_bounds(day: date, timezone: str) -> tuple[datetime, datetime]:
    zone = get_zone(timezone)
    start = datetime.combine(day, time.min, zone)
    return start, start + timedelta(days=1)


def current_day_bounds(timezone: str) -> tuple[datetime, datetime]:
    now = now_in_timezone(timezone)
    return local_day_bounds(now.date(), timezone)


def current_week_bounds(timezone: str) -> tuple[datetime, datetime]:
    now = now_in_timezone(timezone)
    start_day = now.date() - timedelta(days=now.weekday())
    start, _ = local_day_bounds(start_day, timezone)
    return start, start + timedelta(days=7)


def current_month_bounds(timezone: str) -> tuple[datetime, datetime]:
    now = now_in_timezone(timezone)
    start_day = date(now.year, now.month, 1)
    if now.month == 12:
        end_day = date(now.year + 1, 1, 1)
    else:
        end_day = date(now.year, now.month + 1, 1)
    start, _ = local_day_bounds(start_day, timezone)
    end, _ = local_day_bounds(end_day, timezone)
    return start, end


def format_date(value: datetime | date, timezone: str | None = None) -> str:
    if isinstance(value, datetime) and timezone:
        value = value.astimezone(get_zone(timezone))
    return value.strftime("%d.%m.%Y")


def format_time(value: datetime, timezone: str | None = None) -> str:
    if timezone:
        value = value.astimezone(get_zone(timezone))
    return value.strftime("%H:%M")


def dates_between(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def parse_hhmm(value: str, fallback: str = "21:30") -> time:
    source = value or fallback
    try:
        hour, minute = source.split(":", 1)
        return time(hour=int(hour), minute=int(minute))
    except Exception:
        hour, minute = fallback.split(":", 1)
        return time(hour=int(hour), minute=int(minute))
