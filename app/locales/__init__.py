from app.locales.en import MESSAGES as EN_MESSAGES
from app.locales.ru import MESSAGES as RU_MESSAGES
from app.locales.uz import MESSAGES as UZ_MESSAGES

MESSAGES = {
    "ru": RU_MESSAGES,
    "uz": UZ_MESSAGES,
    "en": EN_MESSAGES,
}


def t(lang_code: str | None, key: str, **kwargs: object) -> str:
    lang = lang_code if lang_code in MESSAGES else "ru"
    template = MESSAGES[lang].get(key) or RU_MESSAGES.get(key) or key
    return template.format(**kwargs)
