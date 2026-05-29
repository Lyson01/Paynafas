from app.locales import t


def test_i18n_allows_language_placeholder() -> None:
    text = t(
        "ru",
        "location_ready",
        country="Uzbekistan",
        city="Tashkent",
        currency="UZS",
        timezone="Asia/Tashkent",
        language="Русский",
    )

    assert "Русский" in text
    assert "Asia/Tashkent" in text
