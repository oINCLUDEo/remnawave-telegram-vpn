# Исправление ASGI Ошибок

## Проблема

При попытке зарегистрироваться или выполнить другие операции backend выдает ошибку:

```
Exception in ASGI application
Traceback (most recent call last):
  File "/opt/venv/lib/python3.13/site-packages/uvicorn/protocols/http/h11_impl.py", line 403, in run_asgi
  ...
  File "/opt/venv/lib/python3.13/site-packages/starlette/middleware/base.py", line 191, in __call__
    with recv_stream, send_stream, collapse_excgroups():
```

## Причина

Использование Python 3.10+ синтаксиса union типов (`|`) в FastAPI route decorators:

```python
# ❌ Проблемный код
@router.post('/endpoint', response_model=Type1 | Type2)
```

Проблема:
- Новый синтаксис `|` для union типов появился в Python 3.10
- Не все версии FastAPI/Pydantic корректно его обрабатывают в decorators
- Вызывает runtime exception в ASGI middleware

## Решение

### Шаг 1: Обновить код

Заменить синтаксис `|` на `Union` из `typing`:

```python
# ✅ Правильный код
from typing import Union

@router.post('/endpoint', response_model=Union[Type1, Type2])
```

### Шаг 2: Перезапустить backend

```bash
# Для Docker
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d

# Для локального запуска
# Остановить процесс и запустить заново
python main.py
```

## Проверка работы

### 1. Проверить логи Docker

```bash
docker logs remnawave_bot -f
```

Не должно быть ошибок при запуске.

### 2. Тест регистрации

```bash
curl http://localhost:8081/cabinet/auth/email/register/standalone -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@example.com",
    "password":"TestPass123!",
    "first_name":"Test",
    "last_name":"User",
    "language":"ru"
  }'
```

Должен вернуть успешный ответ (либо токены, либо сообщение о верификации).

### 3. Проверить Swagger UI

Открыть http://localhost:8081/docs

Все endpoints должны отображаться без ошибок.

## Затронутые файлы в нашем исправлении

1. `app/cabinet/routes/auth.py`:
   - `/cabinet/auth/email/register/standalone`

2. `app/cabinet/routes/admin_pinned_messages.py`:
   - `/cabinet/admin/pinned-messages/active`
   - `/cabinet/admin/pinned-messages/active/deactivate`

## Профилактика

### Всегда использовать Union

При создании новых endpoints с несколькими возможными типами ответов:

```python
from typing import Union

# ✅ Правильно
@router.post('/endpoint', response_model=Union[Type1, Type2])
async def my_endpoint():
    ...

# ❌ Избегать
@router.post('/endpoint', response_model=Type1 | Type2)
async def my_endpoint():
    ...
```

### Для Optional типов

```python
from typing import Optional, Union

# ✅ Правильно
@router.get('/endpoint', response_model=Union[MyType, None])
# или
@router.get('/endpoint', response_model=Optional[MyType])

# ❌ Избегать
@router.get('/endpoint', response_model=MyType | None)
```

## Дополнительные причины ASGI ошибок

Если проблема не в union типах, проверьте:

### 1. Validation errors в Pydantic models

```bash
# Проверьте логи на Pydantic validation errors
docker logs remnawave_bot | grep -i "validation"
```

### 2. Несовместимость версий

```bash
# Проверьте версии пакетов
docker exec remnawave_bot pip list | grep -E "fastapi|pydantic|uvicorn"
```

### 3. Проблемы с базой данных

```bash
# Проверьте подключение к PostgreSQL
docker exec remnawave_bot env | grep POSTGRES
```

## Итоговый чек-лист

- [ ] Заменен синтаксис `|` на `Union` в response_model
- [ ] Добавлен импорт `from typing import Union`
- [ ] Backend перезапущен
- [ ] Логи не содержат ошибок
- [ ] Регистрация работает
- [ ] Swagger UI доступен
- [ ] Flutter приложение может подключиться

## Связанные документы

- `FLUTTER_CONNECTION.md` - Настройка подключения Flutter к backend
- `FIX_EMAIL_VERIFICATION.md` - Проблемы с email verification
- `BACKEND_READY_CHECKLIST.md` - Полный чек-лист готовности backend

---

**Статус**: ✅ Исправлено в commit 1468831
