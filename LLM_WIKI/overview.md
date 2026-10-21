# Обзор Ulya VPN

**Ulya VPN** — живой платный VPN-сервис владельца (GitHub `oINCLUDEo`, в коммитах Nikita Zhuklin).
Продаётся через Telegram-бота, у которого есть веб «личный кабинет» и мобильное приложение.
Это источник выручки: любая ошибка в оплатах и подписках бьёт по деньгам и пользователям.

## Компоненты

| Компонент | Что это | Где код |
|---|---|---|
| Telegram-бот | Продажа подписок, баланс, рефералы, поддержка, админка | этот репозиторий, `app/`, `bot/` |
| Бэкенд кабинета | FastAPI-роуты `/cabinet/*`, работают в том же процессе, что бот | `app/cabinet/` |
| Фронтенд кабинета | React-приложение **Bedolaga Cabinet**, стоит как есть, **не форкнуто** | чужой репозиторий `BEDOLAGA-DEV/bedolaga-cabinet` |
| Мобильное приложение | Flutter-клиент Ulya VPN (Android/iOS/desktop) | `dev_vpn/` |
| API для приложения | `/mobile/v1/*` | `app/mobile/` |
| Админ-API | `/api/*`-подобные роуты с токеном (`WEB_API_*`) | `app/webapi/` |
| Аналитика владельца | Google Sheets, учёт расходов и серверов | `bot/` (своё, не из апстрима) |
| VPN-панель | **Remnawave** (отдельный сервис), бот управляет пользователями через её API и получает вебхуки | `app/external/`, `app/services/remnawave_*` |

Домены, встречающиеся в коде: `panel.ulya.space` (панель Remnawave, из `dev_vpn/lib/config/app_config.dart`),
`api.ulya.space` (пример публичного URL бэкенда в `app/config.py`). Deep-link схема приложения: `ulyavpn://`.

## Откуда код

- Репозиторий `oINCLUDEo/remnawave-telegram-vpn` — форк **Bedolaga Bot** (`Fr1ngg/remnawave-bedolaga-telegram-bot`),
  базовая версия апстрима 3.45.2 (`.release-please-manifest.json`). README, CONTRIBUTING и `docs/` — апстримные.
- Стек: Python 3.13, aiogram ≥ 3.25, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 15, Redis 7, structlog, uv.
- Регулярной синхронизации с апстримом в истории `staging` не видно *(не проверено глубже 50 коммитов)*.
  Если тянешь что-то из апстрима — только через владельца, своих правок много (см. ниже).

## Что своё у Ulya (не апстрим)

Всё это лежит в коммитах Nikita Zhuklin и Claude на `staging`:

- Резервный сквад после истечения подписки — [features/reserve-grace.md](features/reserve-grace.md).
- Мобильное приложение и `/mobile/v1`, Google-вход в приложении, IDOR-фикс — [features/mobile-app.md](features/mobile-app.md).
- Google Sheets-аналитика, расходы, серверы — [features/admin-analytics.md](features/admin-analytics.md).
- Тихие часы и одно «живое» напоминание о продлении — [features/notifications.md](features/notifications.md).
- Кастомные премиум-эмодзи на кнопках, единые «Назад»/«Закрыть» (`app/keyboards/common.py`).
- Переделка главного меню (в работе) — [features/main-menu.md](features/main-menu.md).
- Отчёты с когортами (`app/services/reporting_service.py`, коммиты 2026-07-08).

## Пользователи и языки

Локали: ru, en, ua, zh, fa. Основная аудитория русскоязычная *(не проверено по данным)*.
