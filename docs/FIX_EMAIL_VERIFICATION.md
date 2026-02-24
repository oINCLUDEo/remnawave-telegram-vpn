# Решение проблемы "Please verify your email first"

## ⚠️ ОБНОВЛЕНИЕ (новая версия)

**С последним обновлением backend поведение изменилось:**

- Когда `CABINET_EMAIL_VERIFICATION_ENABLED=false`: Registration endpoint **сразу возвращает токены** и автоматически верифицирует email. Пользователь залогинен немедленно! ✅
- Когда `CABINET_EMAIL_VERIFICATION_ENABLED=true`: Работает как раньше - требуется верификация email.

Если вы видите ошибку "TypeError: null is not a subtype of type 'String'" - убедитесь что у вас последняя версия Flutter app и backend.

---

## Проблема

После регистрации через `/cabinet/auth/email/register/standalone` вы не можете войти и получаете ошибку:

```json
{
  "detail": "Please verify your email first"
}
```

## Причина

По умолчанию в backend включена **email verification** (`CABINET_EMAIL_VERIFICATION_ENABLED=true`). Это означает:

1. После регистрации пользователь получает письмо с кодом верификации
2. Пользователь должен ввести этот код через endpoint `/cabinet/auth/email/verify`
3. Только после верификации поле `email_verified` становится `true`
4. Login endpoint проверяет `email_verified` и блокирует вход если `false`

Для локальной разработки это неудобно, так как требует настройки SMTP сервера.

---

## Решения

### ✅ Способ 1: Отключить email verification (рекомендуется для dev)

**Самое простое решение** - отключить проверку верификации глобально.

**Шаги**:

1. Добавьте в `.env`:
   ```env
   CABINET_EMAIL_VERIFICATION_ENABLED=false
   ```

2. Перезапустите backend:
   ```bash
   # Docker
   docker-compose -f docker-compose.local.yml down
   docker-compose -f docker-compose.local.yml up -d
   
   # Или локально
   python main.py
   ```

3. Теперь можно входить сразу после регистрации без верификации!

**Плюсы**:
- ✅ Работает для всех пользователей
- ✅ Не нужно настраивать SMTP
- ✅ Идеально для локальной разработки

**Минусы**:
- ⚠️ НЕ использовать в production!

---

### ✅ Способ 2: Верифицировать пользователей вручную (SQL)

Если у вас уже есть зарегистрированные пользователи, можно верифицировать их вручную через SQL.

**Для конкретного пользователя**:

```bash
# Зайти в PostgreSQL
docker exec -it remnawave_bot_db psql -U remnawave_user -d remnawave_bot

# Верифицировать пользователя
UPDATE users 
SET email_verified = true, 
    email_verified_at = NOW() 
WHERE email = 'test@test.com';

# Проверить
SELECT email, email_verified, email_verified_at FROM users WHERE email = 'test@test.com';

# Выйти
\q
```

**Для всех пользователей** (осторожно!):

```sql
UPDATE users 
SET email_verified = true, 
    email_verified_at = NOW() 
WHERE email_verified = false;
```

**Плюсы**:
- ✅ Работает для отдельных пользователей
- ✅ Не меняет глобальные настройки
- ✅ Можно использовать в production (с осторожностью)

**Минусы**:
- ⚠️ Нужен доступ к PostgreSQL
- ⚠️ Ручная работа для каждого пользователя

---

### ✅ Способ 3: Использовать TEST_EMAIL

Backend поддерживает специальный **тестовый email** который автоматически верифицируется.

**Шаги**:

1. Добавьте в `.env`:
   ```env
   TEST_EMAIL=test@example.com
   TEST_EMAIL_PASSWORD=TestPass123
   ```

2. Перезапустите backend:
   ```bash
   docker-compose -f docker-compose.local.yml down
   docker-compose -f docker-compose.local.yml up -d
   ```

3. Войдите с этим email/password:
   ```bash
   curl http://localhost:8081/cabinet/auth/email/login -X POST \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"TestPass123"}'
   ```

**Как это работает**:
- Если пользователь с `TEST_EMAIL` не существует - создается автоматически при первом входе
- `email_verified` устанавливается в `true` автоматически
- Пароль проверяется через `TEST_EMAIL_PASSWORD`
- Bypass всех проверок верификации

**Плюсы**:
- ✅ Автоматическое создание тестового пользователя
- ✅ Не нужна база данных или SQL
- ✅ Удобно для тестирования

**Минусы**:
- ⚠️ Работает только для одного email
- ⚠️ НЕ использовать в production!

---

## Диагностика

### Проверка текущих настроек

```bash
# В Docker контейнере
docker exec remnawave_bot env | grep CABINET_EMAIL_VERIFICATION
# Должно показать: CABINET_EMAIL_VERIFICATION_ENABLED=true/false

docker exec remnawave_bot env | grep TEST_EMAIL
# Должно показать: TEST_EMAIL=... и TEST_EMAIL_PASSWORD=...
```

### Проверка статуса пользователя в БД

```bash
docker exec -it remnawave_bot_db psql -U remnawave_user -d remnawave_bot

SELECT id, email, email_verified, email_verified_at, created_at 
FROM users 
WHERE email = 'your@email.com';
```

Результат:
- `email_verified = false` → Нужна верификация
- `email_verified = true` → Можно входить

---

## Рекомендации

### Для локальной разработки ✅

**Лучший вариант**:
```env
CABINET_EMAIL_VERIFICATION_ENABLED=false
```

Это позволит:
- Быстро тестировать регистрацию/вход
- Не настраивать SMTP
- Не возиться с SQL

**Альтернатива** (если нужно тестировать verification flow):
```env
CABINET_EMAIL_VERIFICATION_ENABLED=true
TEST_EMAIL=dev@test.com
TEST_EMAIL_PASSWORD=DevPass123
```

### Для production ⚠️

**Обязательно**:
```env
CABINET_EMAIL_VERIFICATION_ENABLED=true
CABINET_EMAIL_VERIFICATION_EXPIRE_HOURS=24

# НЕ устанавливайте TEST_EMAIL в production!
TEST_EMAIL=
TEST_EMAIL_PASSWORD=
```

**Настройте SMTP** для отправки писем с кодами верификации.

---

## Полная процедура

### Вариант A: Отключить verification (dev)

```bash
# 1. Обновить .env
echo "CABINET_EMAIL_VERIFICATION_ENABLED=false" >> .env

# 2. Перезапустить
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d

# 3. Зарегистрироваться
curl http://localhost:8081/cabinet/auth/email/register/standalone -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "email":"newuser@test.com",
    "password":"TestPass123!",
    "first_name":"New",
    "last_name":"User",
    "language":"ru"
  }'

# 4. Войти (теперь работает!)
curl http://localhost:8081/cabinet/auth/email/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@test.com","password":"TestPass123!"}'

# ✅ Должен вернуть access_token
```

### Вариант B: Верифицировать существующего пользователя (SQL)

```bash
# 1. Зайти в PostgreSQL
docker exec -it remnawave_bot_db psql -U remnawave_user -d remnawave_bot

# 2. Верифицировать
UPDATE users SET email_verified = true, email_verified_at = NOW() WHERE email = 'test@test.com';

# 3. Проверить
SELECT email, email_verified FROM users WHERE email = 'test@test.com';

# 4. Выйти
\q

# 5. Войти
curl http://localhost:8081/cabinet/auth/email/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"YourPassword123!"}'

# ✅ Должен вернуть access_token
```

### Вариант C: Использовать TEST_EMAIL

```bash
# 1. Обновить .env
cat >> .env << EOF
TEST_EMAIL=dev@test.com
TEST_EMAIL_PASSWORD=DevPass123
EOF

# 2. Перезапустить
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d

# 3. Войти (создастся автоматически)
curl http://localhost:8081/cabinet/auth/email/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@test.com","password":"DevPass123"}'

# ✅ Должен вернуть access_token
```

---

## Чек-лист

После применения решения:

- [ ] Backend перезапущен с новыми настройками
- [ ] `CABINET_EMAIL_VERIFICATION_ENABLED` установлен правильно
- [ ] Пользователь может зарегистрироваться
- [ ] Пользователь может войти без ошибки "Please verify your email first"
- [ ] Flutter приложение работает с login/register

---

## Связанные документы

- [FLUTTER_CONNECTION.md](./FLUTTER_CONNECTION.md) - Настройка Flutter с backend
- [BACKEND_READY_CHECKLIST.md](./BACKEND_READY_CHECKLIST.md) - Финальная проверка
- [CABINET_API_REFERENCE.md](./CABINET_API_REFERENCE.md) - API endpoints
