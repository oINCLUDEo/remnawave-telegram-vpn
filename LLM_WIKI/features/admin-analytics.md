# Аналитика владельца: Google Sheets, расходы, серверы (пакет `bot/`)

Своё, не апстрим. Код в корневом пакете `bot/`, хендлеры регистрируются в конце `app/bot.py`, джобы стартуют в `main.py`.
В админке бота блок: «📊 Google Sheets», «🖥 Серверы», «💸 Добавить расход» (`app/keyboards/admin.py`).

## Google Sheets (`bot/export/sheets_sync.py`, `bot/jobs/daily_sheets_sync.py`)

- Ежедневно в 03:00 *(TZ контейнера, МСК)* выгружает данные в таблицу. Вручную: админка → Google Sheets
  (текущий месяц / прошлый / всё).
- Env: `SPREADSHEET_ID`, `GOOGLE_CREDENTIALS_JSON_PATH` (в Docker `/etc/ulya/google_credentials.json`), `SHEETS_STARS_RUB_RATE` (1.3).
- Листы: «Транзакции», «По месяцам», «Метрики», «По тарифам», «Аналитика», когортные («Когорты», «Когорты по источникам»,
  «Retention», «Доход по юзерам»).
- Метрики, которые считает код: активные платящие, новые платящие, отток, MRR (`_compute_mrr_kopeks`), выручка по тарифам,
  реферальные начисления, зачисления/списания баланса, ручные расходы, маржа.
- Маппинг понятий на таблицы БД — в докстринге `sheets_sync.py` (транзакции, `has_had_paid_subscription`, конверсии, …).

## Расходы (`bot/handlers/expense_handler.py`)

FSM: категория (инфраструктура / реклама / прочее) → подкатегория → сумма → дата → комментарий → сохранить.
Таблица `manual_expenses`, создаётся вручную `bot/models/create_expenses_table.sql` (не Alembic). Попадает в Sheets.

## Серверы инфраструктуры (`bot/handlers/server_handler.py`, `bot/jobs/server_reminder.py`)

Учёт VPS: провайдер, локация, фикс/почасовая оплата, дата платежа. Таблица `infrastructure_servers`
(`bot/models/create_servers_table.sql`, вручную). Каждый день в 09:00 МСК напоминание в `ADMIN_NOTIFICATIONS_CHAT_ID`
о серверах, которые надо оплатить в ближайшие `remind_days_before` дней.

⚠️ Возможный конфликт `callback_data='admin_servers'` с серверами панели — см. [../gotchas.md](../gotchas.md) п. 17.

## Встроенные отчёты апстрима

`app/services/reporting_service.py`, `app/handlers/admin/reports.py`: дневной/недельный/месячный отчёт в админке,
доработаны владельцем (когорты, реальные поступления по тарифам, 2026-07-08).
