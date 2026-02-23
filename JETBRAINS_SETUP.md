# Инструкция: Копирование изменений в JetBrains IDE

## Вариант 1: Через Git команды в терминале (Рекомендуется)

Открой терминал в JetBrains IDE (Alt+F12 или View → Tool Windows → Terminal) и выполни:

```bash
# 1. Обнови информацию о ветках
git fetch origin

# 2. Переключись на ветку с моими изменениями
git checkout copilot/create-flutter-app

# 3. Подтяни последние изменения (если нужно)
git pull origin copilot/create-flutter-app
```

**Готово!** Все изменения теперь в твоем проекте.

---

## Вариант 2: Через UI JetBrains IDE

### Способ A: Checkout ветки
1. Внизу IDE нажми на текущую ветку (обычно `main` или `master`)
2. В меню выбери **Remote Branches → origin/copilot/create-flutter-app**
3. Выбери **Checkout**
4. IDE автоматически переключит ветку и скачает изменения

### Способ B: Через Git панель
1. Открой **Git** панель (Alt+9 или View → Tool Windows → Git)
2. Во вкладке **Log** найди ветку `origin/copilot/create-flutter-app`
3. Правый клик → **Checkout**

### Способ C: Через VCS меню
1. Меню **Git → Fetch**
2. Меню **Git → Branches**
3. Найди **origin/copilot/create-flutter-app**
4. Правый клик → **Checkout**

---

## Вариант 3: Если хочешь слить в main

```bash
# 1. Переключись на main
git checkout main

# 2. Подтяни последние изменения main
git pull origin main

# 3. Слей мою ветку
git merge copilot/create-flutter-app

# 4. Если конфликтов нет - запуши
git push origin main
```

---

## Что будет скопировано

### Изменения backend (3 файла)
- `app/config.py` - Добавлен API_ONLY_MODE
- `main.py` - Условный запуск без Telegram бота
- `.env.api-only.example` - Пример конфигурации

### Flutter приложение (20 файлов)
- `flutter_app/` - Полное Flutter приложение
- Все экраны (7 штук)
- API интеграция
- State management
- Navigation
- Theme

### Конфигурация (3 файла)
- `docker-compose.api-only.yml` - Docker Compose для API-only
- `start-api-only.sh` - Скрипт автозапуска
- `.env.api-only.example` - Конфигурация

### Документация (10+ файлов)
- `API_ONLY_QUICKSTART.md`
- `FLUTTER_APP_COMPLETE.md`
- `docs/API_ONLY_MODE.md`
- `flutter_app/QUICKSTART.md`
- И другие...

---

## Проверка после копирования

```bash
# Проверь что ты на правильной ветке
git branch

# Должно показать:
# * copilot/create-flutter-app

# Проверь что файлы есть
ls flutter_app/
ls .env.api-only.example
ls start-api-only.sh
```

---

## Запуск после копирования

### Backend (API-only mode)
```bash
# Автоматически
./start-api-only.sh

# Или вручную
cp .env.api-only.example .env
# Отредактируй .env
docker-compose -f docker-compose.api-only.yml up -d
```

### Flutter app
```bash
cd flutter_app
flutter pub get
flutter run
```

---

## Если возникли проблемы

### "Branch not found"
```bash
git fetch origin
git checkout copilot/create-flutter-app
```

### "Конфликты при merge"
```bash
# Посмотри конфликты
git status

# Отмени merge
git merge --abort

# Используй rebase вместо merge
git rebase copilot/create-flutter-app
```

### "Нет доступа к ветке"
```bash
# Убедись что ты в правильном репозитории
git remote -v

# Должно показать:
# origin https://github.com/oINCLUDEo/remnawave-telegram-vpn.git
```

---

## Альтернатива: Скачать архив

Если Git не работает, скачай архив ветки:

```
https://github.com/oINCLUDEo/remnawave-telegram-vpn/archive/refs/heads/copilot/create-flutter-app.zip
```

Распакуй и скопируй файлы вручную.

---

## Коммиты в этой ветке

Все мои изменения:
1. Initial plan for Flutter app integration
2. Add comprehensive Flutter app integration documentation
3. Add comprehensive Flutter integration summary
4. Add Flutter documentation navigation README
5. Initial plan for API-only mode implementation
6. Implement API-only mode for Flutter app backend
7. Add API-only mode configuration files
8. Add API-only mode startup helper and documentation
9. Add complete Flutter application implementation
10. Add Flutter app quick start and complete guides

Всего ~13 коммитов с полной реализацией.

---

## Быстрая команда (всё в одном)

```bash
git fetch origin && git checkout copilot/create-flutter-app && git pull origin copilot/create-flutter-app
```

**После этого всё готово к работе!** 🚀
