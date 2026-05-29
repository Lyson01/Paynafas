from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="Пропустить")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить расход"), KeyboardButton(text="💰 Добавить доход")],
            [KeyboardButton(text="📊 Отчеты"), KeyboardButton(text="💵 Зарплатный период")],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="⭐ Premium")],
        ],
        resize_keyboard=True,
    )


def onboarding_confirm_keyboard(*, skipped: bool = False) -> InlineKeyboardMarkup:
    first = "Продолжить" if skipped else "Всё верно"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=first, callback_data="onboarding:confirm")],
            [
                InlineKeyboardButton(text="Изменить валюту", callback_data="settings:currency"),
                InlineKeyboardButton(text="Изменить язык", callback_data="settings:language"),
            ],
            [InlineKeyboardButton(text="Изменить часовой пояс", callback_data="settings:timezone")],
        ]
    )


def after_transaction_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Удалить", callback_data=f"tx:delete:{transaction_id}"),
                InlineKeyboardButton(
                    text="Изменить категорию", callback_data=f"tx:category:{transaction_id}"
                ),
            ],
            [InlineKeyboardButton(text="Отчет за сегодня", callback_data="report:today")],
        ]
    )


def salary_offer_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да", callback_data=f"salary:create:{transaction_id}:month"
                ),
                InlineKeyboardButton(text="Нет", callback_data="salary:skip"),
            ]
        ]
    )


def salary_next_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Через месяц", callback_data=f"salary:create:{transaction_id}:month"
                ),
                InlineKeyboardButton(
                    text="25 числа", callback_data=f"salary:create:{transaction_id}:25"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Пропустить", callback_data=f"salary:create:{transaction_id}:skip"
                )
            ],
        ]
    )


def premium_keyboard(
    month_label: str = "1 месяц",
    year_label: str = "1 год",
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=month_label, callback_data="premium:plan:premium_month")],
            [InlineKeyboardButton(text=year_label, callback_data="premium:plan:premium_year")],
            [InlineKeyboardButton(text="Возможности Premium", callback_data="premium:features")],
        ]
    )


def premium_active_keyboard(
    month_label: str = "Продлить на месяц",
    year_label: str = "Продлить на год",
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=month_label, callback_data="premium:plan:premium_month")],
            [InlineKeyboardButton(text=year_label, callback_data="premium:plan:premium_year")],
            [InlineKeyboardButton(text="Возможности Premium", callback_data="premium:features")],
        ]
    )


def payment_methods_keyboard(
    *,
    show_international: bool,
    show_uzbek: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if show_uzbek:
        rows.append(
            [InlineKeyboardButton(text="Uzcard / Humo", callback_data="payment:method:uzcard_humo")]
        )
    if show_international:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Visa / Mastercard", callback_data="payment:method:visa_mastercard"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="Отмена", callback_data="payment:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_invoice_keyboard(invoice_id: int, payment_url: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if payment_url:
        rows.append([InlineKeyboardButton(text="Оплатить", url=payment_url)])
    rows.append(
        [InlineKeyboardButton(text="Проверить оплату", callback_data=f"payment:check:{invoice_id}")]
    )
    rows.append([InlineKeyboardButton(text="Отмена", callback_data=f"payment:cancel:{invoice_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def undo_delete_keyboard(batch_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отменить удаление", callback_data=f"undo_delete:{batch_id}"
                )
            ],
            [InlineKeyboardButton(text="История", callback_data="delete:history")],
        ]
    )


def delete_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Последнюю запись", callback_data="delete:last")],
            [InlineKeyboardButton(text="Выбрать из истории", callback_data="delete:history")],
            [
                InlineKeyboardButton(text="За сегодня", callback_data="delete:preview:today"),
                InlineKeyboardButton(text="За неделю", callback_data="delete:preview:week"),
            ],
            [
                InlineKeyboardButton(text="За месяц", callback_data="delete:preview:month"),
                InlineKeyboardButton(text="За период", callback_data="delete:preview:period"),
            ],
            [InlineKeyboardButton(text="Все записи", callback_data="delete:preview:all")],
            [InlineKeyboardButton(text="Отмена", callback_data="delete:cancel")],
        ]
    )


def delete_confirm_keyboard(delete_type: str, count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Да, удалить {count} записей",
                    callback_data=f"delete:apply:{delete_type}",
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data="delete:cancel")],
        ]
    )


def history_delete_keyboard(
    transaction_ids: list[int],
    *,
    selected_ids: set[int] | None = None,
) -> InlineKeyboardMarkup:
    selected_ids = selected_ids or set()
    rows: list[list[InlineKeyboardButton]] = []
    for index, transaction_id in enumerate(transaction_ids, start=1):
        mark = "✓ " if transaction_id in selected_ids else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark}Выбрать #{index}",
                    callback_data=f"delete:toggle:{transaction_id}",
                ),
                InlineKeyboardButton(
                    text=f"Удалить #{index}",
                    callback_data=f"tx:delete:{transaction_id}",
                ),
            ]
        )
    if transaction_ids:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Удалить выбранные", callback_data="delete:selected_confirm"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="Назад", callback_data="delete:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def transaction_delete_confirm_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, удалить", callback_data=f"tx:confirm_delete:{transaction_id}"
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data="delete:cancel")],
        ]
    )


def report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сегодня", callback_data="report:today"),
                InlineKeyboardButton(text="Неделя", callback_data="report:week"),
            ],
            [
                InlineKeyboardButton(text="Месяц", callback_data="report:month"),
                InlineKeyboardButton(text="Зарплатный период", callback_data="report:period"),
            ],
            [
                InlineKeyboardButton(text="Все время", callback_data="report:alltime"),
                InlineKeyboardButton(text="По категориям", callback_data="report:categories"),
            ],
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Изменить язык", callback_data="settings:language"),
                InlineKeyboardButton(text="Изменить валюту", callback_data="settings:currency"),
            ],
            [InlineKeyboardButton(text="Изменить часовой пояс", callback_data="settings:timezone")],
            [InlineKeyboardButton(text="Напоминания", callback_data="settings:reminders")],
        ]
    )


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Русский", callback_data="set:language:ru"),
                InlineKeyboardButton(text="O‘zbekcha", callback_data="set:language:uz"),
                InlineKeyboardButton(text="English", callback_data="set:language:en"),
            ]
        ]
    )


def currency_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for first, second, third in [("UZS", "USD", "RUB"), ("KZT", "EUR", "GBP")]:
        rows.append(
            [
                InlineKeyboardButton(text=first, callback_data=f"set:currency:{first}"),
                InlineKeyboardButton(text=second, callback_data=f"set:currency:{second}"),
                InlineKeyboardButton(text=third, callback_data=f"set:currency:{third}"),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def timezone_keyboard() -> InlineKeyboardMarkup:
    zones = ["Asia/Tashkent", "Europe/Moscow", "Asia/Almaty", "America/New_York", "Europe/London"]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=zone, callback_data=f"set:timezone:{zone}")]
            for zone in zones
        ]
    )


def reminders_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔕 Не напоминать", callback_data="reminders:disable_daily"
                )
            ],
            [InlineKeyboardButton(text="✅ Сегодня не было трат", callback_data="no_spend:today")],
        ]
    )


def export_keyboard() -> InlineKeyboardMarkup:
    periods = [
        ("Сегодня", "today"),
        ("Неделя", "week"),
        ("Месяц", "month"),
        ("Период", "salary"),
        ("Все время", "alltime"),
    ]
    rows = []
    for title, period in periods:
        rows.append(
            [
                InlineKeyboardButton(text=f"CSV {title}", callback_data=f"export:csv:{period}"),
                InlineKeyboardButton(text=f"XLSX {title}", callback_data=f"export:xlsx:{period}"),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
