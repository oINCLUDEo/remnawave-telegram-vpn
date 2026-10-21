# Архитектура

Подробный автосгенерированный список модулей: `docs/project_structure_reference.md` (апстримный, местами устарел).
Здесь только то, что нужно, чтобы не заблудиться.

## Один процесс

`main.py` (~1100 строк) поднимает всё в одном процессе:

1. Логи (`app/logging_config.py`, отдельный лог платежей).
2. Миграции Alembic (`run_alembic_upgrade`), синхронизация sequence в Postgres.
3. Загрузка настроек из БД поверх `.env` (`bot_configuration_service`, см. ниже).
4. Бот aiogram (`app/bot.py: setup_bot`) — polling или webhook (`BOT_RUN_MODE`, `WEBHOOK_URL`).
5. Единое FastAPI-приложение (`app/webserver/unified_app.py`): кабинет `/cabinet/*`, мобильное API `/mobile/v1/*`,
   вебхуки платёжек (`app/webserver/payments.py`), вебхук Remnawave (`app/webserver/remnawave_webhook.py`),
   вебхук Telegram, `/uploads`, `/miniapp/static`, админ-API (`app/webapi/app.py`).
6. Фоновые сервисы-синглтоны: `monitoring_service` (истечения, автоплатёж, напоминания), `remnawave_sync_service`,
   `payment_verification_service` (автопроверка зависших платежей), `backup_service`, `broadcast_service`,
   `reporting_service`, `traffic_monitoring_scheduler`, `nalogo_queue_service`, `contest_rotation_service`,
   и свои: `bot.jobs.daily_sheets_sync` (03:00), `bot.jobs.server_reminder` (09:00 МСК).

Docker: `docker-compose.yml` = postgres + redis + bot, порт `8080`. Монтируются `./locales`, `./uploads`, `./logs`, `./data`,
`vpn_logo.png`, `/etc/ulya/google_credentials.json`. TZ контейнера `Europe/Moscow`.

## Слои кода (`app/`)

| Слой | Путь | Заметки |
|---|---|---|
| Хендлеры бота | `app/handlers/` | `start.py` (регистрация), `menu.py` (главное меню), `subscription/*` (покупка, продление, трафик, устройства), `balance/*` (по файлу на платёжку), `admin/*` (~40 разделов админки) |
| Клавиатуры | `app/keyboards/` | `inline.py` (огромный), `admin.py`, `common.py` (единые «Назад»/«Закрыть»); на ветке меню: `main_menu.py`, `icons.py` |
| Сервисы | `app/services/` | Вся бизнес-логика. Ключевые: `subscription_service.py` (синк с панелью, grace), `subscription_renewal_service.py`, `subscription_auto_purchase_service.py`, `payment_service.py` + `payment/*`, `remnawave_webhook_service.py`, `monitoring_service.py`, `pricing_engine.py` |
| БД | `app/database/models.py`, `app/database/crud/*` | SQLAlchemy async; деньги в **копейках** (`*_kopeks`) |
| Кабинет | `app/cabinet/routes/*` | Бэкенд для внешнего фронта Bedolaga Cabinet; JWT `get_current_cabinet_user` |
| Мобильное API | `app/mobile/` | Требует тот же JWT кабинета (см. [features/mobile-app.md](features/mobile-app.md)) |
| Админ-API | `app/webapi/` | Токены `WEB_API_*` |
| Внешние API | `app/external/` | Клиент Remnawave и платёжек |
| Утилиты | `app/utils/` | `miniapp_buttons.py` (кнопка «в кабинет или в бота»), `button_styles_cache.py`, `menu_layout_cache.py`, `formatters.py` |

Пакет `bot/` в корне — не апстрим, а своя аналитика владельца ([features/admin-analytics.md](features/admin-analytics.md)).
Его хендлеры регистрируются в конце `app/bot.py: setup_bot`.

## Настройки: два слоя

1. `.env` → `app/config.py: Settings` (pydantic, ~800 полей, пример в `.env.example`).
2. Таблица `system_settings` в БД → `app/services/system_settings_service.py: BotConfigurationService`.
   Значения, изменённые в админке бота («Конфигурация бота») или в админке кабинета, **перекрывают `.env`**
   (кроме ключей из `ENV_OVERRIDE_KEYS`, которые всегда берутся из `.env`).

Следствие: смотреть только `.env`, чтобы понять поведение прода, недостаточно. Значение могли поменять в админке.

## Локализация

- Встроенные тексты: `app/localization/locales/{ru,en,ua,zh,fa}.json`.
- Переопределения: каталог `LOCALES_PATH` (в Docker `./locales` → `/app/locales`), в репозитории это `locales/*.json`.
  `load_locale` сливает их, **переопределение побеждает**. Файлы в `locales/` содержат кастомные `tg-emoji` id.
- Значит, новый ключ нужно добавить в **оба** места, иначе на проде текст может не появиться или быть старым.
- Кастомные премиум-эмодзи на кнопках задаются через `icon_custom_emoji_id` (aiogram ≥ 3.25), цвет через `style`
  (`primary`/`success`/`danger`). Известные id — в [features/main-menu.md](features/main-menu.md).

## Деньги и платежи

- Единый баланс пользователя; покупка подписки списывает с баланса; пополнение через ~15 провайдеров
  (`app/services/payment/*`, `app/handlers/balance/*`, вебхуки в `app/webserver/payments.py`).
- «Корзина» в Redis сохраняет выбор, если не хватает денег; после пополнения `subscription_auto_purchase_service`
  может купить сам (`AUTO_PURCHASE_AFTER_TOPUP_ENABLED`).
- Какие платёжки включены на проде — неизвестно ([open-questions.md](open-questions.md)).
- Реальные поступления: `app/database/crud/transaction.py: REAL_PAYMENT_METHODS` (баланс и бонусы туда не входят).

## Связь с Remnawave

- Бот создаёт/обновляет пользователя в панели (`update_remnawave_user` — ~70 мест вызова), назначает «сквады»
  (наборы серверов), лимит трафика, срок.
- Панель шлёт вебхуки (`user.modified`, `user.expired`, …) → `app/services/remnawave_webhook_service.py`.
  Панель часто шлёт несколько событий подряд и **отвечает вебхуком на наши же изменения** — источник гонок,
  см. [gotchas.md](gotchas.md).
