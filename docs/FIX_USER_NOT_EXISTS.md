# Исправление ошибки "role remnawave_user does not exist"

## ❌ Ошибка в логах PostgreSQL

```
FATAL: role "remnawave_user" does not exist
password authentication failed for user "remnawave_user"
DETAIL: Role "remnawave_user" does not exist.
```

## ✅ Что это означает

**Проблема**: Пользователь `remnawave_user` не существует в PostgreSQL

**Почему это происходит**:
- PostgreSQL контейнер был запущен ранее с другим пользователем (обычно `postgres`)
- Данные сохранились в Docker volume
- При перезапуске контейнера `POSTGRES_USER` игнорируется (работает только при первой инициализации)
- Приложение пытается подключиться как `remnawave_user`, но этого пользователя нет

---

## 🚀 Решение 1: Полная очистка и пересоздание (Рекомендуется)

Это самое простое и надежное решение:

```bash
# Остановить и удалить все контейнеры
docker-compose -f docker-compose.local.yml down

# ВАЖНО: Удалить все volumes (очистит все данные!)
docker-compose -f docker-compose.local.yml down -v

# Или вручную
docker volume rm remnawave-bot-dev_postgres_data
docker volume rm remnawave-bot-dev_redis_data

# Проверить что volumes удалены
docker volume ls | findstr remnawave

# Запустить заново - PostgreSQL создаст пользователя с нуля
docker-compose -f docker-compose.local.yml up -d

# Проверить логи
docker-compose -f docker-compose.local.yml logs postgres
```

**Проверка**:
```bash
# Подождите 10 секунд, затем проверьте
docker exec -it remnawave_bot_db psql -U remnawave_user -d remnawave_bot -c "SELECT current_user;"
```

---

## 🚀 Решение 2: Создать пользователя в существующей БД

Если вы НЕ хотите терять данные:

### Шаг 1: Подключитесь как суперпользователь

```bash
# Подключиться к контейнеру
docker exec -it remnawave_bot_db psql -U postgres
```

Если пользователь `postgres` не работает, попробуйте:
```bash
# Узнать какой пользователь есть
docker exec -it remnawave_bot_db psql -U postgres -c "\du"
```

### Шаг 2: Создайте пользователя и БД

В psql выполните:

```sql
-- Создать пользователя
CREATE USER remnawave_user WITH PASSWORD 'secure_password_123';

-- Создать базу данных (если нет)
CREATE DATABASE remnawave_bot OWNER remnawave_user;

-- Дать все права
GRANT ALL PRIVILEGES ON DATABASE remnawave_bot TO remnawave_user;

-- Дать права на схему public (для PostgreSQL 15+)
\c remnawave_bot
GRANT ALL ON SCHEMA public TO remnawave_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO remnawave_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO remnawave_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO remnawave_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO remnawave_user;

-- Проверить что пользователь создан
\du

-- Выход
\q
```

### Шаг 3: Проверьте подключение

```bash
# Проверить что можете подключиться
docker exec -it remnawave_bot_db psql -U remnawave_user -d remnawave_bot -c "SELECT current_user;"

# Должно вывести: remnawave_user
```

---

## 🚀 Решение 3: Пересоздать только PostgreSQL контейнер

Если используете отдельный контейнер (не docker-compose):

```bash
# Остановить и удалить контейнер И volume
docker stop remnawave_postgres
docker rm remnawave_postgres
docker volume rm postgres_data  # Имя может отличаться

# Создать заново
docker run -d --name remnawave_postgres \
  -e POSTGRES_USER=remnawave_user \
  -e POSTGRES_PASSWORD=secure_password_123 \
  -e POSTGRES_DB=remnawave_bot \
  -p 5432:5432 \
  postgres:15

# Проверить логи
docker logs remnawave_postgres
```

---

## 🔍 Диагностика

### Проверить какие пользователи существуют

```bash
# Способ 1: Через docker exec
docker exec -it remnawave_bot_db psql -U postgres -c "\du"

# Способ 2: Если postgres не работает, проверьте переменные
docker exec -it remnawave_bot_db env | grep POSTGRES
```

### Проверить какие базы существуют

```bash
docker exec -it remnawave_bot_db psql -U postgres -c "\l"
```

### Проверить что volume содержит старые данные

```bash
# Посмотреть volumes
docker volume ls | findstr remnawave

# Информация о volume
docker volume inspect remnawave-bot-dev_postgres_data
```

---

## ⚠️ Важные заметки

1. **POSTGRES_USER работает только при первой инициализации**
   - Если БД уже инициализирована, эта переменная игнорируется
   - Нужно либо удалить volume, либо создать пользователя вручную

2. **Docker volumes сохраняют данные**
   - Даже после `docker-compose down` данные остаются
   - Используйте `docker-compose down -v` для полной очистки

3. **PostgreSQL 15+ требует дополнительных прав**
   - Нужно явно давать права на схему `public`
   - Иначе пользователь не сможет создавать таблицы

---

## 📋 Быстрый чек-лист

После исправления проверьте:

- [ ] PostgreSQL контейнер запущен: `docker ps | findstr postgres`
- [ ] Пользователь существует: `docker exec -it remnawave_bot_db psql -U postgres -c "\du"`
- [ ] База данных существует: `docker exec -it remnawave_bot_db psql -U postgres -c "\l"`
- [ ] Можете подключиться: `docker exec -it remnawave_bot_db psql -U remnawave_user -d remnawave_bot -c "SELECT 1;"`
- [ ] `.env` содержит правильные данные: `type .env | findstr POSTGRES`
- [ ] Приложение запускается: `python main.py`

---

## 🎯 Рекомендация

**Для локальной разработки**:
- Используйте **Решение 1** (полная очистка) - самое простое и быстрое

**Для production или если есть важные данные**:
- Используйте **Решение 2** (создать пользователя вручную)
- Сделайте бэкап перед изменениями

---

## 💡 Предотвращение проблемы

Чтобы избежать в будущем:

1. **При первом запуске сразу используйте правильные переменные**:
   ```yaml
   environment:
     POSTGRES_USER: remnawave_user
     POSTGRES_PASSWORD: secure_password_123
     POSTGRES_DB: remnawave_bot
   ```

2. **Или используйте init скрипт** (создать файл `init-db.sh`):
   ```bash
   #!/bin/bash
   psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
       CREATE USER remnawave_user WITH PASSWORD 'secure_password_123';
       CREATE DATABASE remnawave_bot OWNER remnawave_user;
       GRANT ALL PRIVILEGES ON DATABASE remnawave_bot TO remnawave_user;
   EOSQL
   ```

3. **Документируйте какой пользователь используется** в `.env`

---

## 📚 Дополнительные ресурсы

- [FIX_PASSWORD_ERROR.md](FIX_PASSWORD_ERROR.md) - Ошибки аутентификации
- [WINDOWS_SETUP.md](WINDOWS_SETUP.md) - Полное руководство для Windows
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres) - Официальная документация
