# Руководство по локальному запуску на Windows

Это руководство поможет вам запустить backend на Windows без Docker Compose.

## Проблемы и решения

### 1. Docker Compose: "network remnawave-network declared as external, but could not be found"

**Причина**: Внешняя сеть `remnawave-network` используется только если у вас есть RemnaWave панель в Docker.

**Решение**: Используйте обновленный `docker-compose.local.yml` - внешняя сеть теперь закомментирована и опциональна.

```bash
docker-compose -f docker-compose.local.yml up -d
```

Если вы используете внешнюю панель RemnaWave:
1. Создайте сеть: `docker network create remnawave-network`
2. Раскомментируйте строки с `remnawave-network` в `docker-compose.local.yml`

---

### 2. PostgreSQL: "connection was closed in the middle of operation"

**Причина**: PostgreSQL не запущен на `localhost:5432` или недоступен.

**Решение**: Запустите PostgreSQL одним из способов ниже.

---

## Запуск PostgreSQL на Windows

### Вариант 1: Docker (Рекомендуется)

Самый простой способ - запустить только PostgreSQL и Redis через Docker:

```bash
# Запустить PostgreSQL
docker run -d --name remnawave_postgres ^
  -e POSTGRES_PASSWORD=secure_password_123 ^
  -e POSTGRES_DB=remnawave_bot ^
  -e POSTGRES_USER=remnawave_user ^
  -p 5432:5432 ^
  postgres:15

# Запустить Redis
docker run -d --name remnawave_redis ^
  -p 6379:6379 ^
  redis:7-alpine

# Проверить что запущены
docker ps
```

**Остановка**:
```bash
docker stop remnawave_postgres remnawave_redis
docker rm remnawave_postgres remnawave_redis
```

---

### Вариант 2: Docker Compose только для БД

Используйте `docker-compose.local.yml` только для базы данных:

```bash
# Запустить только postgres и redis
docker-compose -f docker-compose.local.yml up -d postgres redis

# Проверить статус
docker-compose -f docker-compose.local.yml ps

# Остановить
docker-compose -f docker-compose.local.yml down
```

Затем запустите bot через Python:
```bash
python main.py
```

---

### Вариант 3: Установка PostgreSQL на Windows

1. **Скачать PostgreSQL**:
   - Зайдите на https://www.postgresql.org/download/windows/
   - Скачайте и установите PostgreSQL 15
   - При установке задайте пароль для пользователя `postgres`

2. **Создать БД и пользователя**:
   ```sql
   -- Запустите psql или pgAdmin
   CREATE USER remnawave_user WITH PASSWORD 'secure_password_123';
   CREATE DATABASE remnawave_bot OWNER remnawave_user;
   GRANT ALL PRIVILEGES ON DATABASE remnawave_bot TO remnawave_user;
   ```

3. **Установить Redis**:
   - Скачайте Redis для Windows: https://github.com/microsoftarchive/redis/releases
   - Или используйте WSL/Docker для Redis

---

## Настройка .env файла для локального запуска

Создайте файл `.env` (если еще нет):

```bash
copy .env.example .env
```

Убедитесь что в `.env` установлено:

```env
# Для локального запуска на Windows
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=remnawave_bot
POSTGRES_USER=remnawave_user
POSTGRES_PASSWORD=secure_password_123

# Redis
REDIS_URL=redis://localhost:6379/0

# Web API
WEB_API_ENABLED=true
WEB_API_PORT=8081

# Если не используете Telegram бота
TELEGRAM_BOT_ENABLED=false
```

---

## Запуск приложения

### Через Python (локально)

```bash
# 1. Убедитесь что PostgreSQL и Redis запущены
# Проверьте доступность
psql -h localhost -U remnawave_user -d remnawave_bot

# 2. Установите зависимости (первый раз)
pip install -r requirements.txt

# 3. Запустите приложение
python main.py
```

### Через Docker Compose (полностью)

```bash
# Запустить все сервисы (postgres, redis, bot)
docker-compose -f docker-compose.local.yml up -d

# Просмотр логов
docker-compose -f docker-compose.local.yml logs -f bot

# Остановить
docker-compose -f docker-compose.local.yml down
```

---

## Проверка работы

После запуска проверьте:

```bash
# API доступно
curl http://localhost:8081/api/health

# PostgreSQL доступен
psql -h localhost -U remnawave_user -d remnawave_bot -c "SELECT 1;"

# Redis доступен
redis-cli ping
```

---

## Troubleshooting

### Ошибка: "port is already allocated" (Docker)

Порт уже используется другим процессом.

**Решение**:
```bash
# Найти процесс использующий порт 5432
netstat -ano | findstr :5432

# Убить процесс (замените PID)
taskkill /PID <номер_процесса> /F

# Или измените порт в docker-compose
```

### Ошибка: "connection refused"

PostgreSQL не запущен или не слушает порт.

**Решение**:
```bash
# Проверьте запущен ли Docker контейнер
docker ps

# Или проверьте Windows службу PostgreSQL
services.msc
# Найдите "postgresql" и запустите
```

### Ошибка: "password authentication failed"

Неправильный пароль или пользователь.

**Решение**:
- Проверьте `.env` файл
- Убедитесь что пароль в `.env` совпадает с PostgreSQL
- Пересоздайте Docker контейнер:
  ```bash
  docker rm -f remnawave_postgres
  docker run -d --name remnawave_postgres ...
  ```

### Ошибка: "database does not exist"

База данных не создана.

**Решение**:
```bash
# Подключитесь к PostgreSQL
psql -h localhost -U remnawave_user -d postgres

# Создайте БД
CREATE DATABASE remnawave_bot;
```

---

## Полезные команды

### Docker

```bash
# Просмотр запущенных контейнеров
docker ps

# Просмотр логов
docker logs remnawave_postgres
docker logs remnawave_redis

# Подключение к контейнеру
docker exec -it remnawave_postgres psql -U remnawave_user -d remnawave_bot

# Очистка всего
docker-compose -f docker-compose.local.yml down -v
```

### PostgreSQL

```bash
# Подключиться к БД
psql -h localhost -U remnawave_user -d remnawave_bot

# Список таблиц
\dt

# Список БД
\l

# Выход
\q
```

### Redis

```bash
# Проверка подключения
redis-cli ping

# Список ключей
redis-cli keys "*"

# Очистка всех данных
redis-cli FLUSHALL
```

---

## Рекомендации

1. **Для разработки**: Используйте Docker для PostgreSQL и Redis, запускайте Python локально
2. **Для production**: Используйте полный Docker Compose
3. **Бэкапы**: Настройте регулярное резервное копирование PostgreSQL
4. **Безопасность**: Измените пароли в `.env` на более сложные

---

## Поддержка

Если проблемы продолжаются:

1. Проверьте логи приложения: `logs/bot.log`
2. Проверьте логи Docker: `docker-compose logs`
3. Убедитесь что все порты свободны: `netstat -ano`
4. Проверьте версии: Python 3.11+, PostgreSQL 15+, Redis 7+
