# LLM_WIKI — база знаний для агентов Ulya VPN

Эта папка для ИИ-агентов (Claude Code, Copilot, будущий агент-менеджер), которые работают с Ulya VPN.
Цель: новый агент за 5 минут понимает, что это за продукт, как устроен код, что можно трогать и где грабли.

Читай в таком порядке:

1. [overview.md](overview.md) — что такое Ulya VPN, из чего состоит, где что живёт.
2. [workflow.md](workflow.md) — ветки, staging, тесты, что требует согласия владельца. **Обязательно.**
3. [gotchas.md](gotchas.md) — грабли, на которых уже были инциденты в проде. **Обязательно перед правкой подписок/оплат.**
4. [architecture.md](architecture.md) — процессы, слои кода, настройки, локализация, БД.
5. Раздел нужной фичи в [features/](features/).

Для бизнес-задач (метрики, выручка, расходы, отчёты, планирование): [business/](business/).

## Карта

| Файл | О чём |
|---|---|
| [overview.md](overview.md) | Продукт, компоненты, домены, репозитории |
| [workflow.md](workflow.md) | Git, staging → прод, тесты, линт, правила коммитов и PR |
| [architecture.md](architecture.md) | `main.py`, aiogram, FastAPI, сервисы, БД, Redis, настройки, локали |
| [gotchas.md](gotchas.md) | Известные ловушки и инциденты |
| [features/main-menu.md](features/main-menu.md) | Главное меню бота: как было, что переделывается |
| [features/reserve-grace.md](features/reserve-grace.md) | Резервный сквад после истечения подписки (своя фича Ulya) |
| [features/notifications.md](features/notifications.md) | Напоминания, тихие часы, заблокировавшие бота |
| [features/mobile-app.md](features/mobile-app.md) | Flutter-приложение `dev_vpn` и API `/mobile/v1` |
| [features/admin-analytics.md](features/admin-analytics.md) | Google Sheets, расходы, серверы инфраструктуры (пакет `bot/`) |
| [business/README.md](business/README.md) | Для агента-менеджера / помощника CEO: где брать цифры, как считать |
| [decisions.md](decisions.md) | Решения владельца (с датами) |
| [open-questions.md](open-questions.md) | Что ещё неизвестно и кого спросить |
| [CHANGELOG.md](CHANGELOG.md) | История изменений самой вики |

## Правила ведения вики

- Пиши факты, которые нельзя быстро вывести из кода: зачем так сделано, что ломалось, что решил владелец.
  Структуру кода не переписывай построчно, давай пути к файлам (`app/services/subscription_service.py`).
- Каждое утверждение, которое не проверено по коду, помечай *(не проверено)*.
- Решение владельца → [decisions.md](decisions.md) с датой. Неизвестное → [open-questions.md](open-questions.md).
- Изменил поведение, описанное здесь, в том же PR обнови страницу вики и [CHANGELOG.md](CHANGELOG.md).
- Секретов, токенов, паролей, личных данных пользователей здесь не бывает. Telegram ID пользователей тоже не пиши.
- Язык: русский (владелец пишет по-русски), идентификаторы кода как в коде.
- Даты абсолютные (2026-10-21), не «вчера».

Ответственный за вику: отдельный тред агента «LLM_WIKI для агентов» в проекте Ulya VPN.
