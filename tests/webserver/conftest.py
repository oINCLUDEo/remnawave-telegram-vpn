"""Конфигурация pytest для тестов webserver/mobile API.

Устанавливает BACKUP_LOCATION до импорта модулей приложения,
чтобы BackupService не пытался создать директорию /app/data/backups.
Также подменяет отсутствующий в текущей сборке подпакет yookassa.domain.exceptions.
"""

from __future__ import annotations

import os
import sys
import types


os.environ.setdefault('BACKUP_LOCATION', '/tmp/test_backups')  # noqa: S108

# В некоторых окружениях yookassa установлена, но yookassa.domain является
# файлом (не пакетом), поэтому yookassa.domain.exceptions недоступен.
# Добавляем заглушку, если модуль ещё не зарегистрирован.
if 'yookassa.domain.exceptions' not in sys.modules:
    _exc_module = types.ModuleType('yookassa.domain.exceptions')
    _not_found_module = types.ModuleType('yookassa.domain.exceptions.not_found_error')

    class _FakeNotFoundError(Exception):
        pass

    _not_found_module.NotFoundError = _FakeNotFoundError
    sys.modules.setdefault('yookassa.domain.exceptions', _exc_module)
    sys.modules.setdefault('yookassa.domain.exceptions.not_found_error', _not_found_module)
