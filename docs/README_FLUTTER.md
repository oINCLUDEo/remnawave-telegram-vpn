# 📱 Flutter Integration Documentation

Полная документация для создания мобильного приложения на Flutter, которое интегрируется с backend API этого проекта.

## 🚀 С чего начать?

### 1. Быстрый обзор
Начните с **[FLUTTER_SUMMARY.md](./FLUTTER_SUMMARY.md)** - краткая справка о том, что было создано и как это использовать.

### 2. Первое приложение (5 минут)
Следуйте **[FLUTTER_QUICKSTART.md](./FLUTTER_QUICKSTART.md)** для создания базового Flutter приложения с аутентификацией и отображением баланса.

### 3. Полное руководство
Изучите **[FLUTTER_INTEGRATION.md](./FLUTTER_INTEGRATION.md)** для детального понимания всех возможностей API и примеров интеграции.

## 📚 Структура документации

### Для начинающих
1. **[FLUTTER_SUMMARY.md](./FLUTTER_SUMMARY.md)** (10 KB)
   - Что было сделано
   - Как начать использовать
   - Преимущества Flutter приложения
   - Следующие шаги

2. **[FLUTTER_QUICKSTART.md](./FLUTTER_QUICKSTART.md)** (14 KB)
   - 5-минутный quick start
   - Простой API клиент
   - Базовые экраны
   - Примеры кода

### Для разработчиков
3. **[FLUTTER_INTEGRATION.md](./FLUTTER_INTEGRATION.md)** (25 KB)
   - Полное руководство по интеграции
   - Все API endpoints с примерами
   - Аутентификация (Email, Telegram)
   - Платежи (YooKassa, Telegram Stars)
   - WebSocket уведомления
   - Deep links
   - Безопасность
   - Тестирование

4. **[API_REFERENCE.md](./API_REFERENCE.md)** (21 KB)
   - Справочник всех API endpoints
   - Форматы запросов и ответов
   - HTTP статус коды
   - Типы данных
   - Rate limiting
   - WebSocket протокол

### Для архитекторов
5. **[FLUTTER_ARCHITECTURE.md](./FLUTTER_ARCHITECTURE.md)** (26 KB)
   - Диаграммы архитектуры
   - Clean Architecture
   - BLoC pattern
   - Dependency Injection
   - Docker Compose
   - Nginx конфигурация
   - CI/CD pipeline
   - Production checklist

### Конфигурация
6. **[.env.flutter.example](./.env.flutter.example)** (12 KB)
   - Пример конфигурации .env
   - Все настройки Cabinet API
   - Платежные системы
   - Безопасность
   - Feature flags

7. **[README_FLUTTER_SECTION.md](./README_FLUTTER_SECTION.md)** (7 KB)
   - Текст для основного README
   - Обзор Flutter поддержки

## 🎯 Быстрые ссылки

### По функциям

#### Аутентификация
- Email регистрация: [FLUTTER_INTEGRATION.md#post-authregister-email](./FLUTTER_INTEGRATION.md#post-cabinetauthregister-email)
- Email вход: [FLUTTER_INTEGRATION.md#post-authlogin-email](./FLUTTER_INTEGRATION.md#post-cabinetauthlogin-email)
- Telegram Widget: [FLUTTER_INTEGRATION.md#post-authtelegram-widget](./FLUTTER_INTEGRATION.md#post-cabinetauthtelegram-widget)
- Refresh token: [FLUTTER_INTEGRATION.md#post-authrefresh](./FLUTTER_INTEGRATION.md#post-cabinetauthrefresh)

#### Баланс и платежи
- Получить баланс: [API_REFERENCE.md#get-balance](./API_REFERENCE.md#get-balance)
- Пополнить баланс: [API_REFERENCE.md#post-balancetop-up](./API_REFERENCE.md#post-balancetop-up)
- YooKassa интеграция: [FLUTTER_INTEGRATION.md#yookassa-сбп](./FLUTTER_INTEGRATION.md#yookassa-сбп)
- Telegram Stars: [FLUTTER_INTEGRATION.md#telegram-stars](./FLUTTER_INTEGRATION.md#telegram-stars)

#### Подписки
- Текущая подписка: [API_REFERENCE.md#get-subscription](./API_REFERENCE.md#get-subscription)
- Список тарифов: [API_REFERENCE.md#get-subscriptiontariffs](./API_REFERENCE.md#get-subscriptiontariffs)
- Покупка подписки: [API_REFERENCE.md#post-subscriptionpurchase-tariff](./API_REFERENCE.md#post-subscriptionpurchase-tariff)

#### Архитектура
- Clean Architecture: [FLUTTER_ARCHITECTURE.md#clean-architecture](./FLUTTER_ARCHITECTURE.md#clean-architecture-реализация)
- BLoC паттерн: [FLUTTER_ARCHITECTURE.md#presentation-layer](./FLUTTER_ARCHITECTURE.md#3-presentation-layer-bloc)
- Deployment: [FLUTTER_ARCHITECTURE.md#развертывание](./FLUTTER_ARCHITECTURE.md#развертывание-backend-для-flutter)

## 💡 Частые вопросы

### Нужно ли изменять backend код?
**Нет!** Backend уже полностью готов. Нужно только активировать Cabinet API в `.env`:
```env
CABINET_ENABLED=true
CABINET_JWT_SECRET=your-secret-key
```

### Какие платежные системы поддерживаются?
- ✅ YooKassa СБП (Система Быстрых Платежей)
- ✅ YooKassa карты
- ✅ Telegram Stars
- ✅ CryptoBot
- ✅ Другие (см. документацию)

### Как мигрировать пользователей с Telegram бота?
Пользователи могут:
1. Войти через Telegram Widget Auth - все данные сохраняются
2. Зарегистрироваться через email - новые пользователи
3. Использовать оба интерфейса параллельно

### Нужно ли знать Python для Flutter разработки?
**Нет!** Backend работает как REST API. Вы работаете только с HTTP запросами.

### Где живая документация API?
После запуска backend:
- Swagger UI: `https://your-domain.com/docs`
- ReDoc: `https://your-domain.com/redoc`
- OpenAPI JSON: `https://your-domain.com/openapi.json`

## 🛠 Инструменты

### Swagger UI
Интерактивная документация с возможностью тестирования API прямо в браузере.

### Postman Collection
Вы можете импортировать OpenAPI JSON в Postman для тестирования endpoints.

### Code Generation
Генерация Dart клиента из OpenAPI спецификации:
```bash
openapi-generator-cli generate \
  -i https://your-domain.com/openapi.json \
  -g dart-dio \
  -o lib/api_client
```

## 📖 Дополнительные ресурсы

### Flutter
- [Flutter Documentation](https://flutter.dev/docs)
- [Dart Language](https://dart.dev)
- [Flutter Packages](https://pub.dev)

### State Management
- [BLoC Pattern](https://bloclibrary.dev)
- [Provider](https://pub.dev/packages/provider)
- [Riverpod](https://riverpod.dev)

### Architecture
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Flutter Architecture Samples](https://github.com/brianegan/flutter_architecture_samples)

### Backend
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [PostgreSQL](https://www.postgresql.org/docs/)
- [Docker](https://docs.docker.com)

## 🆘 Поддержка

### Сообщество
- **Telegram чат:** https://t.me/+wTdMtSWq8YdmZmVi
- **GitHub Issues:** https://github.com/oINCLUDEo/remnawave-telegram-vpn/issues

### Backend
- **Основной README:** [../README.md](../README.md)
- **API Docs:** https://your-domain.com/docs

## 📝 Примеры проектов

Хотите увидеть готовый пример? Проверьте:
- **Cabinet WebApp:** https://github.com/BEDOLAGA-DEV/bedolaga-cabinet/
- **Telegram Bot:** https://t.me/zero_ping_vpn_bot

## 🤝 Вклад

Нашли ошибку в документации? Хотите улучшить примеры?
1. Создайте Issue
2. Отправьте Pull Request
3. Напишите в Telegram чат

## 📄 Лицензия

MIT License - см. [../LICENSE](../LICENSE)

---

**Удачи в разработке! 🚀**

Начните с [FLUTTER_SUMMARY.md](./FLUTTER_SUMMARY.md) для быстрого обзора.
