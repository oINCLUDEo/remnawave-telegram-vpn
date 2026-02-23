# API-Only Mode - Backend для Flutter приложения

Режим API-only позволяет запустить backend без Telegram бота, используя только Cabinet API для мобильных и веб приложений.

## 🎯 Для чего нужен API-only режим

- ✅ Полная независимость от Telegram
- ✅ Работает только REST API для Flutter/React Native/Web приложений
- ✅ Отключены все Telegram-зависимые функции
- ✅ Меньше потребление ресурсов
- ✅ Простая разработка и отладка на localhost

## 🚀 Быстрый старт на localhost

### Вариант 1: Docker Compose (рекомендуется)

1. **Создайте .env файл:**
```bash
cp .env.api-only .env
```

2. **Настройте обязательные параметры в .env:**
```env
# Секретный ключ для JWT (сгенерируйте!)
CABINET_JWT_SECRET=your-super-secret-jwt-key-min-32-chars

# RemnaWave API
REMNAWAVE_API_URL=https://your-panel.example.com
REMNAWAVE_API_KEY=your_api_key

# YooKassa (опционально)
YOOKASSA_ENABLED=true
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
```

3. **Запустите сервисы:**
```bash
docker-compose -f docker-compose.api-only.yml up -d
```

4. **Проверьте работу:**
```bash
# Swagger документация
open http://localhost:8000/docs

# Cabinet API
curl http://localhost:8000/cabinet/info
```

### Вариант 2: Локальный запуск (без Docker)

1. **Установите зависимости:**
```bash
# PostgreSQL
docker run -d --name vpn-postgres -p 5432:5432 \
  -e POSTGRES_DB=vpn_db \
  -e POSTGRES_USER=vpn_user \
  -e POSTGRES_PASSWORD=vpn_password_123 \
  postgres:15

# Redis
docker run -d --name vpn-redis -p 6379:6379 redis:7-alpine

# Python зависимости
pip install -r requirements.txt
```

2. **Создайте .env файл:**
```bash
cp .env.api-only .env
# Отредактируйте .env - установите CABINET_JWT_SECRET, REMNAWAVE_API_URL, etc.
```

3. **Запустите миграции:**
```bash
alembic upgrade head
```

4. **Запустите backend:**
```bash
python main.py
```

5. **API доступен:**
- Cabinet API: http://localhost:8000/cabinet
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📋 Что работает в API-only режиме

### ✅ Работает
- **Cabinet API** - полный REST API для приложений
- **Аутентификация** - JWT, Email, Telegram Widget
- **Платежи** - YooKassa, Telegram Stars (через HTTP API)
- **Подписки** - создание, продление, управление
- **Реферальная система** - статистика, начисления
- **Тикеты поддержки** - создание, ответы
- **WebSocket** - real-time уведомления
- **Web API** - админ панель через HTTP API
- **База данных** - PostgreSQL с миграциями
- **Кэширование** - Redis
- **Синхронизация** - RemnaWave API
- **Бекапы** - автоматические бекапы БД (без уведомлений в Telegram)

### ❌ Отключено
- **Telegram бот** - polling и webhook
- **Aiogram handlers** - команды и клавиатуры бота
- **Уведомления в Telegram** - админские оповещения
- **Рассылки через бота** - broadcast сообщения
- **Игры и конкурсы** - колесо фортуны, конкурсы рефералов
- **Проверка подписки на канал** - требует бота

## 🔧 Конфигурация

### Обязательные параметры

```env
# Режим API-only
API_ONLY_MODE=true

# Cabinet API (обязательно!)
CABINET_ENABLED=true
CABINET_JWT_SECRET=your-secret-key-min-32-chars

# База данных
DATABASE_URL=******localhost:5432/vpn_db

# RemnaWave API
REMNAWAVE_API_URL=https://your-panel.com
REMNAWAVE_API_KEY=your_api_key
```

### CORS для Flutter приложения

```env
# Разрешите origins для вашего приложения
CABINET_ALLOWED_ORIGINS=myapp://,http://localhost:3000,https://yourdomain.com
```

### Платежные системы

```env
# YooKassa СБП и карты
YOOKASSA_ENABLED=true
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Telegram Stars (работает через HTTP API)
TELEGRAM_STARS_ENABLED=true
TELEGRAM_STARS_RATE_RUB=1.79
```

## 🧪 Тестирование API

### Swagger UI
Интерактивная документация с возможностью тестирования:
```
http://localhost:8000/docs
```

### Примеры запросов

**Регистрация пользователя:**
```bash
curl -X POST http://localhost:8000/cabinet/auth/register-email \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!",
    "first_name": "Test User"
  }'
```

**Вход:**
```bash
curl -X POST http://localhost:8000/cabinet/auth/login-email \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!"
  }'
```

**Получить баланс:**
```bash
curl -X GET http://localhost:8000/cabinet/balance \
  -H "Authorization: ******"
```

**Получить подписку:**
```bash
curl -X GET http://localhost:8000/cabinet/subscription \
  -H "Authorization: ******"
```

## 📱 Интеграция с Flutter

После запуска backend в API-only режиме:

1. **Базовый URL:** `http://localhost:8000/cabinet` (для разработки)
2. **Swagger документация:** Используйте для изучения всех endpoints
3. **Примеры кода:** См. `docs/FLUTTER_QUICKSTART.md`
4. **Полное руководство:** См. `docs/FLUTTER_INTEGRATION.md`

### Быстрый пример Flutter

```dart
import 'package:dio/dio.dart';

class ApiClient {
  static const baseUrl = 'http://localhost:8000/cabinet';
  final dio = Dio(BaseOptions(baseUrl: baseUrl));

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await dio.post('/auth/login-email', data: {
      'email': email,
      'password': password,
    });
    return response.data;
  }
}
```

## 🐛 Отладка

### Логи
```bash
# Просмотр логов в реальном времени
tail -f logs/bot.log

# С Docker
docker-compose -f docker-compose.api-only.yml logs -f api
```

### Проверка здоровья сервисов
```bash
# PostgreSQL
docker exec vpn-postgres pg_isready -U vpn_user

# Redis
docker exec vpn-redis redis-cli ping

# API
curl http://localhost:8000/docs
```

### Частые проблемы

**1. База данных не подключается**
```bash
# Проверьте что PostgreSQL запущен
docker ps | grep postgres

# Проверьте логи
docker logs vpn-postgres
```

**2. JWT токен не работает**
```bash
# Убедитесь что CABINET_JWT_SECRET установлен в .env
# Минимум 32 символа!
grep CABINET_JWT_SECRET .env
```

**3. CORS ошибки**
```bash
# Добавьте origins в CABINET_ALLOWED_ORIGINS
CABINET_ALLOWED_ORIGINS=http://localhost:3000,myapp://
```

## 📊 Мониторинг

### Healthcheck endpoint
```bash
curl http://localhost:8000/docs
```

### Метрики базы данных
```bash
docker exec vpn-postgres psql -U vpn_user -d vpn_db -c "
  SELECT schemaname, tablename, n_live_tup 
  FROM pg_stat_user_tables 
  ORDER BY n_live_tup DESC;"
```

### Redis статистика
```bash
docker exec vpn-redis redis-cli info stats
```

## 🔄 Миграция с Telegram бота

Если у вас уже работает Telegram бот и вы хотите перейти на API-only:

1. **Сделайте бекап БД:**
```bash
docker exec vpn-postgres pg_dump -U vpn_user vpn_db > backup.sql
```

2. **Остановите бота:**
```bash
docker-compose down
```

3. **Измените конфигурацию:**
```bash
# В .env установите
API_ONLY_MODE=true
```

4. **Запустите в API-only режиме:**
```bash
docker-compose -f docker-compose.api-only.yml up -d
```

5. **Все данные сохранятся** - пользователи, подписки, баланс, рефералы

## 🚀 Production deployment

Для production используйте:

1. **HTTPS обязателен!**
```env
CABINET_URL=https://api.yourdomain.com/cabinet
```

2. **Сильные секреты:**
```bash
# Генерация секретного ключа
openssl rand -hex 32
```

3. **Nginx reverse proxy:**
```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;
    
    location /cabinet {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. **Rate limiting и security:**
См. `docs/FLUTTER_ARCHITECTURE.md` для деталей

## 📚 Документация

- **API Reference:** `docs/API_REFERENCE.md` - полный справочник endpoints
- **Flutter Integration:** `docs/FLUTTER_INTEGRATION.md` - руководство по интеграции
- **Architecture:** `docs/FLUTTER_ARCHITECTURE.md` - архитектура и deployment
- **Quick Start:** `docs/FLUTTER_QUICKSTART.md` - быстрый старт Flutter приложения

## 💬 Поддержка

- **GitHub Issues:** https://github.com/oINCLUDEo/remnawave-telegram-vpn/issues
- **Telegram чат:** https://t.me/+wTdMtSWq8YdmZmVi
- **Swagger UI:** http://localhost:8000/docs

## ✅ Checklist для первого запуска

- [ ] PostgreSQL запущен
- [ ] Redis запущен
- [ ] .env файл создан и настроен
- [ ] CABINET_JWT_SECRET установлен (32+ символов)
- [ ] REMNAWAVE_API_URL и REMNAWAVE_API_KEY настроены
- [ ] Миграции выполнены (`alembic upgrade head`)
- [ ] Backend запущен (`python main.py`)
- [ ] Swagger UI доступен (http://localhost:8000/docs)
- [ ] Тестовая регистрация работает
- [ ] Тестовый вход работает

---

**Готово к разработке Flutter приложения! 🚀**

Начните с создания простого экрана входа, следуя `docs/FLUTTER_QUICKSTART.md`
