# Исправление ошибки "password authentication failed"

## ❌ Ошибка

```
password authentication failed for user "remnawave_user"
```

## ⚠️ Сначала проверьте логи PostgreSQL!

Если в логах PostgreSQL вы видите:
```
FATAL: role "remnawave_user" does not exist
```

**ЭТО ДРУГАЯ ПРОБЛЕМА!** Перейдите к [FIX_USER_NOT_EXISTS.md](FIX_USER_NOT_EXISTS.md)

---

## ✅ Что это означает (если пользователь существует)

✅ **Хорошая новость**: PostgreSQL запущен и работает!  
❌ **Проблема**: Пароль в вашем `.env` файле не совпадает с паролем в PostgreSQL

## 🔧 Быстрое решение

### Вариант 1: Пересоздать PostgreSQL (Docker) - Проще всего

```bash
# Остановить и удалить старый контейнер
docker stop remnawave_postgres
docker rm remnawave_postgres

# Создать новый с правильным паролем
docker run -d --name remnawave_postgres ^
  -e POSTGRES_PASSWORD=secure_password_123 ^
  -e POSTGRES_DB=remnawave_bot ^
  -e POSTGRES_USER=remnawave_user ^
  -p 5432:5432 ^
  postgres:15

# Проверить что работает
docker ps
```

### Вариант 2: Изменить пароль в PostgreSQL

```bash
# Подключитесь к PostgreSQL как суперпользователь
docker exec -it remnawave_postgres psql -U postgres

# В psql выполните:
ALTER USER remnawave_user WITH PASSWORD 'secure_password_123';
\q
```

### Вариант 3: Изменить пароль в .env

Если вы помните какой пароль установлен в PostgreSQL, просто измените `.env`:

```env
# В файле .env
POSTGRES_PASSWORD=ваш_реальный_пароль
```

## 📋 Проверка после исправления

```bash
# 1. Проверьте что можете подключиться
psql -h localhost -U remnawave_user -d remnawave_bot
# Введите пароль: secure_password_123

# 2. Если подключение успешно, запустите бот
python main.py

# Или Docker Compose
docker-compose -f docker-compose.local.yml up -d
```

## 🔍 Диагностика

### Где какой пароль установлен?

**В .env файле**:
```bash
type .env | findstr POSTGRES_PASSWORD
```

**В Docker контейнере**:
```bash
docker inspect remnawave_postgres | findstr POSTGRES_PASSWORD
```

**Проверить подключение вручную**:
```bash
# Попробуйте разные пароли
psql -h localhost -U remnawave_user -d postgres

# Если ошибка "password authentication failed" - пароль неверный
# Если просит ввести пароль и потом подключается - пароль верный!
```

## 💡 Рекомендуемые пароли

Для **локальной разработки** используйте простой пароль:
```env
POSTGRES_PASSWORD=secure_password_123
```

Для **production** используйте сложный пароль:
```env
POSTGRES_PASSWORD=your_very_strong_password_here_123!@#
```

## 🎯 Итоговый чек-лист

- [ ] PostgreSQL запущен (`docker ps` или `services.msc`)
- [ ] Порт 5432 открыт (`netstat -an | findstr :5432`)
- [ ] `.env` файл существует в корне проекта
- [ ] `POSTGRES_PASSWORD` установлен в `.env`
- [ ] Пароль в `.env` совпадает с PostgreSQL
- [ ] База данных `remnawave_bot` создана
- [ ] Пользователь `remnawave_user` существует
- [ ] Можете подключиться через `psql` вручную

## ❓ Все еще не работает?

Попробуйте **полный сброс**:

```bash
# 1. Остановить все
docker-compose -f docker-compose.local.yml down -v

# 2. Удалить старые контейнеры и volumes
docker rm -f remnawave_postgres remnawave_redis
docker volume rm $(docker volume ls -q | findstr remnawave)

# 3. Проверить .env
type .env | findstr POSTGRES

# 4. Запустить заново
docker-compose -f docker-compose.local.yml up -d

# 5. Подождать 10 секунд и проверить
docker-compose -f docker-compose.local.yml logs postgres
```

## 📚 Дополнительная информация

- [Полное руководство по Windows](WINDOWS_SETUP.md)
- [Настройка API-only режима](API_ONLY_MODE.md)
- [PostgreSQL документация](https://www.postgresql.org/docs/)
