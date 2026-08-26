"""In-memory store for backend-driven mobile in-app notifications.

Administrators can push notifications via the bot admin panel or directly
via this store.  The store is intentionally simple — notifications are kept
in memory and reset on restart.  A future improvement could persist them in
the database.

Usage (from admin handlers or other services):

    from app.services.mobile_notification_store import mobile_notification_store

    mobile_notification_store.push(
        id='maintenance_2024',
        title='Технические работы',
        body='Плановые работы 15 марта с 02:00 до 04:00 МСК.',
        type='persistent',
        severity='warning',
    )

    mobile_notification_store.remove('maintenance_2024')
"""

from __future__ import annotations

import threading
from typing import Any


class MobileNotificationStore:
    """Thread-safe in-memory store for mobile in-app notifications."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._notifications: list[dict[str, Any]] = []

    # ── Mutation ──────────────────────────────────────────────────────────────

    def push(
        self,
        *,
        id: str,
        title: str,
        body: str,
        type: str = 'informational',
        severity: str = 'info',
        auto_dismiss_seconds: int = 5,
    ) -> None:
        """Add or replace a notification by *id*."""
        entry: dict[str, Any] = {
            'id': id,
            'title': title,
            'body': body,
            'type': type,
            'severity': severity,
            'auto_dismiss_seconds': auto_dismiss_seconds,
        }
        with self._lock:
            # Replace existing entry with same id
            self._notifications = [n for n in self._notifications if n['id'] != id]
            self._notifications.append(entry)

    def remove(self, notification_id: str) -> bool:
        """Remove a notification by id.  Returns True if it existed."""
        with self._lock:
            before = len(self._notifications)
            self._notifications = [n for n in self._notifications if n['id'] != notification_id]
            return len(self._notifications) < before

    def clear(self) -> None:
        """Remove all notifications."""
        with self._lock:
            self._notifications = []

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_active(self) -> list[dict[str, Any]]:
        """Return a snapshot of all active notifications."""
        with self._lock:
            return list(self._notifications)

    def __len__(self) -> int:
        with self._lock:
            return len(self._notifications)


# Singleton instance used throughout the application
mobile_notification_store = MobileNotificationStore()
