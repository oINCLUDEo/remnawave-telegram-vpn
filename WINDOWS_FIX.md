# Исправление ошибки API-Only Mode на Windows

## Проблема (исправлена ✅)

При запуске контейнера `vpn_api` на Windows возникала ошибка:
```
Traceback (most recent call last):
  File "/app/main.py", line 13, in 
```

## Решение

Убран импорт `setup_bot` из верхнего уровня файла. Теперь бот импортируется только когда `API_ONLY_MODE=false`.

## Тестирование на Windows

### 1. Обнови код

```bash
git fetch origin
git checkout copilot/create-flutter-app
git pull origin copilot/create-flutter-app
```

### 2. Проверь конфигурацию

Убедись что в `.env` или docker-compose есть:
```env
API_ONLY_MODE=true
BOT_TOKEN=  # Может быть пустым в API-only режиме
```

### 3. Пересобери и запусти контейнеры

```bash
# Останови текущие контейнеры
docker-compose -f docker-compose.api-only.yml down

# Удали старый образ
docker-compose -f docker-compose.api-only.yml rm -f api

# Пересобери образ
docker-compose -f docker-compose.api-only.yml build --no-cache api

# Запусти
docker-compose -f docker-compose.api-only.yml up -d
```

### 4. Проверь логи

```bash
# Смотри логи контейнера
docker-compose -f docker-compose.api-only.yml logs -f api

# Должно появиться:
# ✅ "API_ONLY_MODE=true (работает только Cabinet API)"
# ✅ "HTTP-сервисы активны"
# ✅ "Startup completed"
```

### 5. Проверь что API работает

```bash
# Windows PowerShell
Invoke-WebRequest http://localhost:8000/docs

# Или в браузере
http://localhost:8000/docs
```

Должен открыться Swagger UI.

## Что изменилось

**Было:**
```python
# main.py строка 13
from app.bot import setup_bot  # ❌ Всегда импортируется

# Позже...
if not settings.is_api_only_mode():
    bot, dp = await setup_bot()
```

**Стало:**
```python
# main.py строка 13
# (импорт удален)

# Позже...
if not settings.is_api_only_mode():
    from app.bot import setup_bot  # ✅ Импорт только когда нужен
    bot, dp = await setup_bot()
```

## Если проблема осталась

### Проверь переменные окружения

```bash
# Посмотри что передается в контейнер
docker-compose -f docker-compose.api-only.yml config | grep API_ONLY_MODE

# Должно быть:
# API_ONLY_MODE: "true"
```

### Проверь логи полностью

```bash
docker-compose -f docker-compose.api-only.yml logs api > api_logs.txt
```

Отправь файл `api_logs.txt` для анализа.

### Очисти Docker кеш (если rebuild не помог)

```bash
# Полная очистка (осторожно - удалит ВСЕ неиспользуемые образы)
docker system prune -a

# Потом пересобери
docker-compose -f docker-compose.api-only.yml build --no-cache
docker-compose -f docker-compose.api-only.yml up -d
```

## Технические детали

### Почему возникала ошибка

1. `import app.bot` выполнялся на уровне модуля (строка 13)
2. В `app/bot.py` создается `Bot(token=settings.BOT_TOKEN)`
3. Когда `BOT_TOKEN` пустой (валидно для API-only), aiogram может выбрасывать ошибку
4. Ошибка происходила ДО проверки `is_api_only_mode()`

### Почему это исправляет проблему

1. Импорт `setup_bot` происходит только внутри `if not is_api_only_mode()`
2. В API-only режиме `app.bot` вообще не импортируется
3. Не требуется валидный `BOT_TOKEN` для запуска в API-only режиме

## Дополнительно: Windows-специфичные настройки

### Если используешь WSL2

Убедись что Docker Desktop настроен правильно:
- Settings → General → Use WSL 2 based engine ✅
- Settings → Resources → WSL Integration → Enable integration

### Если Docker на нативном Windows

Убедись что:
- Docker Desktop запущен
- В настройках включен "Expose daemon on tcp://localhost:2375 without TLS" (если используешь docker через CLI)

### Монтирование томов на Windows

Если видишь ошибки с томами `./logs` или `./data`:

```yaml
# В docker-compose.api-only.yml измени пути:
volumes:
  - C:/path/to/your/project/logs:/app/logs     # Абсолютный путь Windows
  - C:/path/to/your/project/data:/app/data     # Абсолютный путь Windows
```

Или создай Named volumes:
```yaml
volumes:
  - vpn_logs:/app/logs
  - vpn_data:/app/data

volumes:
  postgres_data:
    driver: local
  vpn_logs:
    driver: local
  vpn_data:
    driver: local
```

---

**Проблема исправлена! API-only режим должен запуститься на Windows.** 🚀

Если остались вопросы - покажи полные логи контейнера.
