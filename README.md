# Telegram-бот для учета доходов и расходов

Production-ready проект Telegram-бота на Python 3.12, aiogram 3, PostgreSQL, Redis, SQLAlchemy 2 async, Alembic и APScheduler.

Бот помогает вести личный учет денег от зарплаты до зарплаты: пользователь пишет расходы и доходы обычным текстом, а бот сохраняет операции, считает остаток по текущему зарплатному периоду, строит отчеты и отправляет напоминания.

## Возможности

- регистрация без телефона и SMS, пользователь определяется по `telegram_id`;
- хранение данных в PostgreSQL, данные не пропадают после перезапуска;
- onboarding с опциональной геолокацией;
- ручной выбор языка, валюты и часового пояса;
- парсинг сообщений вроде `кофе 25000`, `вчера продукты 120000`, `аренда 300$`, `зп 5 млн`;
- отчеты за день, неделю, месяц, зарплатный период и все время;
- no-spend days через кнопку `Сегодня не было трат`;
- ежедневные напоминания через APScheduler;
- безопасное удаление одной записи, выбранных записей и массовое soft delete;
- восстановление последнего удаления в течение `DELETE_UNDO_TTL_HOURS`;
- Premium-логика с платежными счетами, mock provider для разработки и webhook;
- экспорт CSV/XLSX для Premium;
- админ-панель в Telegram.

## Создание Telegram-бота

1. Откройте Telegram и найдите `@BotFather`.
2. Отправьте `/newbot`.
3. Укажите имя бота.
4. Укажите username, который заканчивается на `bot`.
5. BotFather выдаст `BOT_TOKEN`.

## Настройка .env

Скопируйте пример:

```bash
cp .env.example .env
```

Заполните минимум:

```env
BOT_TOKEN=your_token_here
ADMIN_IDS=123456789
```

`ADMIN_IDS` — Telegram ID администраторов через запятую. Узнать свой ID можно через ботов вроде `@userinfobot`.

По умолчанию бот использует:

```env
DEFAULT_TIMEZONE=Asia/Tashkent
DEFAULT_CURRENCY=UZS
DEFAULT_LANGUAGE=ru
```

Для локальной разработки платежи уже работают в mock-режиме:

```env
PAYMENTS_ENABLED=true
INTERNATIONAL_PAYMENT_PROVIDER=mock
UZBEK_PAYMENT_PROVIDER=mock
PUBLIC_WEBHOOK_BASE_URL=http://localhost:8000
```

`PUBLIC_WEBHOOK_BASE_URL` нужен, чтобы кнопка оплаты в Telegram вела на web-сервис. На VPS укажите публичный HTTPS URL.

## Запуск через Docker Compose

```bash
docker compose up --build -d
```

Compose поднимает сервисы:

- `postgres` — основная база данных;
- `redis` — FSM aiogram, временные callback/session данные и кеш;
- `bot` — Telegram polling;
- `web` — FastAPI для платежных webhook и mock-оплаты.

Контейнер `bot` при старте автоматически выполняет `alembic upgrade head`, поэтому база поднимается сразу. Миграции также можно применить вручную:

```bash
docker compose exec bot alembic upgrade head
```

Посмотреть логи:

```bash
docker compose logs -f bot
docker compose logs -f web
```

Остановить:

```bash
docker compose down
```

## Простой бесплатный хостинг

Самый простой вариант без сложной Oracle-регистрации:

- Koyeb — один бесплатный контейнер;
- Neon — бесплатный PostgreSQL;
- Upstash — бесплатный Redis.

Минус: бесплатные PaaS-тарифы могут менять лимиты или усыплять сервисы. Для реально стабильного 24/7 лучше VPS, но для старта Koyeb проще.

Для одного контейнера есть отдельный Dockerfile:

```text
Dockerfile.single
```

Он запускает сразу:

- `alembic upgrade head`;
- `uvicorn app.web.main:app`;
- `python -m app.main`.

Настройки для хоста:

```bash
cp .env.host.example .env
```

В Koyeb укажите:

```text
Dockerfile: Dockerfile.single
Port: 8000
Health check path: /health
```

Переменные окружения:

```env
BOT_TOKEN=...
ADMIN_IDS=6048168849
LIFETIME_PREMIUM_TELEGRAM_IDS=6048168849
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=rediss://...
PUBLIC_WEBHOOK_BASE_URL=https://your-koyeb-app.koyeb.app
```

Важно: `DATABASE_URL` и `REDIS_URL` должны быть внешними, не локальными `postgres`/`redis`, потому что на бесплатном PaaS в одном контейнере нет docker-compose volume.

## Деплой на Railway

Проект подготовлен для Railway через `requirements.txt` и `Procfile`.

Стартовая команда в `Procfile`:

```text
worker: sh -c "alembic upgrade head && python -m app.main"
```

Миграции Alembic применяются перед запуском бота. Основной файл бота: `app/main.py`, запуск через Python module path `python -m app.main`.

### Как клонировать проект

```bash
git clone <your-repository-url>
cd uchot
```

### Railway Variables

В Railway Dashboard откройте проект → `Variables` и добавьте переменные из `.env.example`. Минимальный набор:

```env
BOT_TOKEN=your_real_telegram_bot_token
ADMIN_IDS=6048168849
LIFETIME_PREMIUM_TELEGRAM_IDS=6048168849
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB
REDIS_URL=redis://default:PASSWORD@HOST:PORT
DEFAULT_TIMEZONE=Asia/Tashkent
DEFAULT_CURRENCY=UZS
DEFAULT_LANGUAGE=ru
```

Если Railway PostgreSQL выдает URL вида `postgresql://...`, замените схему на `postgresql+asyncpg://...`.

Если Redis URL начинается с `rediss://`, оставьте `rediss://`.

Для платежных ссылок:

```env
PUBLIC_WEBHOOK_BASE_URL=https://your-railway-domain.up.railway.app
```

Если запускаете только `worker`, webhooks и mock payment page не будут публично доступны. Для платежных webhook нужен отдельный Railway service с командой:

```bash
uvicorn app.web.main:app --host 0.0.0.0 --port $PORT
```

### Как задеплоить через Railway UI

1. Загрузите проект в GitHub.
2. Откройте Railway.
3. Нажмите `New Project`.
4. Выберите `Deploy from GitHub repo`.
5. Выберите репозиторий с ботом.
6. В `Variables` добавьте переменные окружения.
7. Убедитесь, что Railway использует `Procfile`.
8. Нажмите `Deploy`.
9. В логах должно быть:

```text
Bot started
Start polling
```

Для PostgreSQL и Redis можно использовать Railway plugins или внешние Neon/Upstash. Главное: не хранить данные бота в памяти приложения.

## Проверка работы

1. Запустите проект.
2. Откройте созданного бота в Telegram.
3. Напишите `/start`.
4. Отправьте геолокацию или нажмите `Пропустить`.
5. Напишите `зарплата 5000000`.
6. Нажмите `Через месяц` или `Пропустить`.
7. Напишите `кофе 25000`.
8. Проверьте `/today`, `/period`, `/balance`.
9. Откройте `/premium`, выберите тариф и оплату в mock-режиме.
10. Нажмите `Проверить оплату`: Premium должен активироваться.
11. Откройте `/history`, удалите запись и восстановите через `/undo_delete`.
12. Перезапустите контейнер `bot` и снова напишите `/start`: бот найдет пользователя по `telegram_id`, а Premium и операции останутся в PostgreSQL.

## Регистрация по Telegram ID

Бот не просит номер телефона и не использует SMS OTP. При `/start` он берет `message.from_user.id`, ищет пользователя в таблице `users.telegram_id`, а если записи нет — создает `User` и `UserSettings`.

Поле `telegram_id` уникально в базе. Повторный `/start` загружает существующего пользователя и его настройки из PostgreSQL.

## Геолокация

Геолокация необязательна. Если пользователь отправляет ее, бот:

- определяет часовой пояс через `timezonefinder`;
- пытается определить страну и город через Nominatim;
- подбирает валюту, язык и формат по стране;
- по умолчанию не сохраняет точные координаты.

За приватность отвечает настройка:

```env
SAVE_RAW_LOCATION=false
```

Если reverse geocoding недоступен, бот продолжает работать с fallback-настройками.

## Напоминания

APScheduler запускает фоновые проверки:

- ежедневное напоминание в `daily_reminder_time`, если за текущий локальный день нет expense-операций и пользователь не отмечал no-spend day;
- напоминание перед ожидаемой следующей зарплатой.

Команда:

```text
/reminders
```

Кнопка `Сегодня не было трат` создает запись в `no_spend_days` с уникальностью `user_id + date`.

## Экспорт

Экспорт доступен Premium-пользователям:

```text
/export
```

Форматы:

- CSV;
- XLSX.

Периоды:

- сегодня;
- неделя;
- месяц;
- зарплатный период;
- все время.

## Premium и оплата

Команда:

```text
/premium
```

Free:

- до 50 операций в месяц;
- базовые отчеты;
- история последних 10 операций;
- ежедневные напоминания.

Premium:

- безлимитные операции;
- полный отчет по зарплатному периоду;
- all-time отчет;
- CSV/XLSX экспорт;
- прогноз до следующей зарплаты;
- расширенная история.

Оплата построена через abstraction `PaymentProvider`:

```python
create_payment_link(...)
verify_webhook(...)
get_payment_status(...)
```

Бизнес-логика не привязана к конкретному эквайрингу. В проекте есть провайдеры:

- `mock` — локальная разработка и тесты;
- `international_card` — адаптер для Visa/Mastercard;
- `uzbek_card` — адаптер для Uzcard/Humo.

Если пользователь из Узбекистана или его валюта `UZS`, бот показывает `Uzcard / Humo` и `Visa / Mastercard`, если способы включены. Для остальных стран показывается `Visa / Mastercard`.

Бот не хранит данные банковских карт, не принимает номер карты, срок действия или CVV в Telegram. Пользователь оплачивает только на защищенной странице платежного провайдера. В базе хранятся только `PaymentInvoice`, статус, сумма, тариф и provider ids.

### Mock-платежи

В `.env`:

```env
INTERNATIONAL_PAYMENT_PROVIDER=mock
UZBEK_PAYMENT_PROVIDER=mock
PUBLIC_WEBHOOK_BASE_URL=http://localhost:8000
```

Пользователь выбирает тариф в `/premium`, получает ссылку оплаты и открывает ее. Также админ может симулировать оплату:

```text
/mock_pay INVOICE_ID
```

Mock provider нельзя использовать в production.

### Подключение Visa/Mastercard

Укажите настройки реального провайдера в `.env`:

```env
INTERNATIONAL_PAYMENTS_ENABLED=true
INTERNATIONAL_PAYMENT_PROVIDER=your_provider
INTERNATIONAL_PAYMENT_PUBLIC_KEY=
INTERNATIONAL_PAYMENT_SECRET_KEY=
INTERNATIONAL_PAYMENT_WEBHOOK_SECRET=
INTERNATIONAL_PAYMENT_SUCCESS_URL=https://your-domain/success
INTERNATIONAL_PAYMENT_CANCEL_URL=https://your-domain/cancel
```

Текущий adapter сделан как безопасная заготовка: без конкретного SDK он не принимает карточные данные и не создает фейковые платежи. Для production подключите SDK/API выбранного PSP внутри `ConfiguredExternalPaymentProvider`.

### Подключение Uzcard/Humo

```env
UZBEK_PAYMENTS_ENABLED=true
UZBEK_PAYMENT_PROVIDER=your_uzbek_provider
UZBEK_PAYMENT_MERCHANT_ID=
UZBEK_PAYMENT_SECRET_KEY=
UZBEK_PAYMENT_SERVICE_ID=
UZBEK_PAYMENT_WEBHOOK_SECRET=
UZBEK_PAYMENT_SUCCESS_URL=https://your-domain/success
UZBEK_PAYMENT_CANCEL_URL=https://your-domain/cancel
```

Webhook URL:

```text
https://your-domain/webhooks/payments/international_card
https://your-domain/webhooks/payments/uzbek_card
https://your-domain/webhooks/payments/mock
```

Webhook idempotent: повторный `paid` для уже оплаченного `PaymentInvoice` не продлевает подписку второй раз.

### Где хранится Premium

Premium — только PostgreSQL:

- `users.plan`;
- `users.premium_until`;
- `subscriptions`;
- `payment_invoices`.

Redis не является источником правды для Premium, оплат, подписок, доходов или расходов. После перезапуска контейнера, сервера или `redis flushall` Premium не теряется.

При каждом действии бот проверяет Premium через БД. Если `premium_until < now`, пользователь переводится на `free`, а активные подписки помечаются `expired`.

Для владельца можно задать вечный Premium через:

```env
LIFETIME_PREMIUM_TELEGRAM_IDS=6048168849
```

При первом действии такого пользователя бот сохранит в PostgreSQL `User.plan=premium`, `premium_until=9999-12-31` и активную `Subscription`.

## Удаление записей

Команды:

```text
/delete_last
/delete
/clear
/undo_delete
```

Меню `/delete` позволяет удалить:

- последнюю запись;
- конкретную запись из истории;
- несколько выбранных записей;
- все записи за сегодня;
- все записи за неделю;
- все записи за месяц;
- все записи текущего зарплатного периода;
- все записи пользователя.

Все удаления безопасные: физического удаления из `transactions` нет, ставится `is_deleted=true`. Перед массовым удалением бот показывает количество записей и спрашивает подтверждение. Отчеты, баланс, экспорт, напоминания и free-limit учитывают только `is_deleted=false`.

Для восстановления создается `DeleteBatch` и `DeleteBatchItem`. Команда `/undo_delete` или кнопка `Отменить удаление` восстанавливает последний batch в течение `DELETE_UNDO_TTL_HOURS`.

Пользователь может удалять только свои записи: все действия дополнительно проверяют `transaction.user_id == current_user.id`, даже если вручную подставить чужой `transaction_id` в callback.

## Админ-панель

Админом считается пользователь с `is_admin=true` в БД или `telegram_id` из `ADMIN_IDS`.

Команды:

```text
/admin
/admin stats
/admin users
/admin payments
/admin approve PAYMENT_ID
/admin reject PAYMENT_ID
/admin grant TELEGRAM_ID DAYS
/admin revoke TELEGRAM_ID
/admin broadcast текст рассылки
/mock_pay INVOICE_ID
```

Команды `/admin approve` и `/admin reject` оставлены для legacy ручных `PaymentRequest`. Онлайн-оплата активирует Premium через `PaymentInvoice` и webhook автоматически.

При одобрении legacy-заявки бот:

- ставит `PaymentRequest.status=approved`;
- переводит пользователя на `premium`;
- выставляет `premium_until`;
- создает `Subscription`;
- уведомляет пользователя.

## Команды пользователя

```text
/start
/help
/today
/week
/month
/period
/alltime
/balance
/categories
/history
/delete
/delete_last
/clear
/undo_delete
/no_spend_today
/reminders
/settings
/premium
/export
```

## Деплой на VPS

1. Установите Docker и Docker Compose plugin.
2. Скопируйте проект на сервер.
3. Создайте `.env`.
4. Укажите `BOT_TOKEN`, `ADMIN_IDS`, платежные настройки и публичный `PUBLIC_WEBHOOK_BASE_URL`.
5. Запустите:

```bash
docker compose up --build -d
```

6. Проверьте логи:

```bash
docker compose logs -f bot
docker compose logs -f web
```

Для обновления:

```bash
git pull
docker compose up --build -d
```

## Локальная разработка

```bash
pip install -e ".[dev]"
pytest
ruff check .
black --check .
```

Через Makefile:

```bash
make test
make lint
make format
```
