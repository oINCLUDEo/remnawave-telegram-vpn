# Ulya VPN — инструкции для агентов

Это Telegram-бот платного VPN Ulya VPN (форк Bedolaga Bot, aiogram 3 + FastAPI + PostgreSQL + Redis).
Сервис живой и приносит деньги: ошибки в подписках и оплатах сразу бьют по пользователям.

**Начни с [LLM_WIKI/README.md](LLM_WIKI/README.md).** Минимум перед любой правкой: `LLM_WIKI/workflow.md` и `LLM_WIKI/gotchas.md`.

Коротко:

- Рабочая ветка `staging`. Свои изменения — в ветке от `staging`, PR в `staging`. `main`/`dev` устарели.
- Без явного согласия владельца: не пушить в `staging`, не мерджить, не трогать прод, прод-БД, панель Remnawave,
  цены и рассылки.
- Перед PR: `uv run ruff format --check . && uv run ruff check . && uv run pytest`. Базовая линия: 88 failed / 446 passed.
- `.gitignore` — белый список: новая папка в корне не попадёт в git без `!папка/**`.
- Тексты для пользователей — во все 5 локалей и в оба каталога (`locales/`, `app/localization/locales/`).
- Изменил поведение, описанное в `LLM_WIKI/`, — обнови страницу и `LLM_WIKI/CHANGELOG.md` в том же PR.
- Владелец пишет по-русски, отвечай по-русски.
