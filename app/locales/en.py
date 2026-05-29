MESSAGES = {
    "start_new": (
        "Hi! I will help you control money from salary to salary.\n\n"
        "Just send expenses in plain text:\n"
        "— coffee 25000\n"
        "— taxi 18000\n"
        "— yesterday groceries 120000\n"
        "— salary 5000000\n\n"
        "You can send location so I set currency, language and report time correctly.\n"
        "It is optional."
    ),
    "start_existing": "Good to see you again. Let's continue.",
    "main_menu": "Main menu",
    "location_ready": (
        "Done, I configured the bot for you:\n\n"
        "Country: {country}\n"
        "City: {city}\n"
        "Currency: {currency}\n"
        "Timezone: {timezone}\n"
        "Language: {language}\n\n"
        "Is everything correct?"
    ),
    "location_default": (
        "Ok, I used default settings:\n\n"
        "Currency: {currency}\n"
        "Timezone: {timezone}\n"
        "Language: {language}\n\n"
        "You can change this in settings."
    ),
    "registration_done": "Done. Now send expenses and income in plain text.",
    "unknown_amount": "I could not find the amount. Try: coffee 25000, taxi 18000, salary 5000000",
    "expense_saved": (
        "Saved expense:\n"
        "{emoji} {title} — {amount}\n\n"
        "Date: {date}\n"
        "Time: {time}\n"
        "Category: {category}\n\n"
        "{balance_line}"
    ),
    "income_saved": (
        "Saved income:\n"
        "{emoji} {title} — {amount}\n\n"
        "Date: {date}\n"
        "Time: {time}\n\n"
        "{salary_line}"
    ),
    "balance_line": "Salary balance: {amount}",
    "no_period_offer": "Want to set salary so I can track the balance until the next one?",
    "salary_offer": "Create a new salary period?",
    "salary_next_prompt": "When is the next salary? Choose or type: in a month, 25, June 10, skip",
    "period_created": "Salary period created.",
    "operation_deleted": "Last operation deleted.",
    "nothing_to_delete": "No operations to delete.",
    "no_spend_saved": "Marked: no spending today. A good day for the budget.",
    "no_spend_has_expense": "There are already expenses today, so I will not mark it as no-spend.",
    "free_limit": (
        "You used {limit} free records this month.\n\n"
        "Premium gives unlimited records and export.\n\n"
        "Price: {price} UZS/month"
    ),
    "premium_info": (
        "Premium: unlimited records, full reports, Excel export, forecast, all-time history.\n\n"
        "Price: {monthly_price} UZS/month or {yearly_price} UZS/year.\n\n"
        "Pay to card: {card}, then send a receipt here."
    ),
    "receipt_prompt": "Send a photo or document with the payment receipt.",
    "receipt_saved": "Receipt sent to admin. I will notify you after approval.",
    "premium_required": "This feature requires Premium.",
    "reminder_daily": (
        "You have not recorded any expenses today.\n\n"
        "Send: coffee 25000 or taxi 18000.\n\n"
        "Or press the button if there were no expenses."
    ),
    "reminder_disabled": "Daily reminders disabled.",
    "salary_reminder": "New salary is coming soon. Want to see the current period summary?",
    "settings": "Settings:\nCurrency: {currency}\nTimezone: {timezone}\nLanguage: {language}",
    "help": (
        "Examples:\n"
        "coffee 25000\n"
        "yesterday groceries 120000\n"
        "salary 5000000\n\n"
        "Commands: /today /week /month /period /balance /history "
        "/delete_last /settings /premium /export"
    ),
}
