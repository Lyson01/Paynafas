import re
from html import escape


def clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def html(value: str | None) -> str:
    return escape(value or "", quote=False)


def normalize_language(language_code: str | None) -> str | None:
    if not language_code:
        return None
    language = language_code.lower().split("-")[0].split("_")[0]
    return language if language in {"ru", "uz", "en"} else None
