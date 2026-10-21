# Мобильное приложение и `/mobile/v1`

## Клиент

`dev_vpn/` — Flutter-приложение Ulya VPN (Android, iOS, macOS, Windows, web). Своё, не апстрим.
Конфиг: `dev_vpn/lib/config/app_config.dart` (`panelBaseUrl = https://panel.ulya.space`; `backendBaseUrl` там
сейчас локальный dev-адрес — не прод). Страницы: `lib/pages/` (home, servers, premium, subscription, settings, logs).
Deep-link схема `ulyavpn://`. Папка `flutter_app/` в истории — ранний прототип, в рабочем дереве её нет.

Сборка/релиз приложения в этом репозитории не автоматизированы *(не проверено, где публикуется)*.

## Бэкенд

`app/mobile/routes/`: `auth`, `config`, `me`, `notifications`, `servers`, `subscription`, `support`, `tariffs`.

- Все `/mobile/v1/*` требуют **Bearer JWT кабинета** (`Depends(get_current_cabinet_user)`), как `/cabinet/*` (`be16b19d`).
  Заодно работают блэклист, техработы и проверка обязательных каналов.
- Вход: Telegram OIDC и email через `/cabinet/auth/*`; Google — через `GET /cabinet/auth/oauth/{provider}/authorize?mobile=1`
  → `/mobile-callback` → редирект `ulyavpn://oauth/done?token=...` → `POST /cabinet/auth/login/auto` (`23e6ee17`).
  Для прода нужен `MOBILE_OAUTH_API_BASE_URL` и доп. redirect URI в Google Cloud Console.
  Реферальный код при Google-входе поддерживается (`896175b6`).
- Покупки: флаг `use_balance` в buy/upgrade/buy-tariff/tariff-switch; при нехватке создаётся платёж YooKassa + корзина
  (`08bad995`). Типы платежей должны быть в `_MOBILE_PAYMENT_TYPES` (`payment_verification_service.py`).
- Удалённый конфиг для клиента: `MOBILE_*` настройки (мин. сборка, force update, техработы, блок-лист приложений),
  категория MOBILE в админке бота (`1e60220f`, `c4b8bb52`).
- Гостевой каталог серверов `GET /mobile/v1/servers` — хосты панели минус скрытые админом (`f675030b`).

Тесты: `tests/mobile/`, `tests/cabinet/test_oauth_mobile_callback.py`.
