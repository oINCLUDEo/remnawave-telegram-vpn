"""Tests for MobileNotificationStore."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from app.services.mobile_notification_store import MobileNotificationStore


def _store() -> MobileNotificationStore:
    """Return a fresh store for each test."""
    return MobileNotificationStore()


# ---------------------------------------------------------------------------


def test_empty_store_returns_empty_list():
    store = _store()
    assert store.get_active() == []
    assert len(store) == 0


def test_push_adds_notification():
    store = _store()
    store.push(id='n1', title='Title', body='Body')
    items = store.get_active()
    assert len(items) == 1
    assert items[0]['id'] == 'n1'
    assert items[0]['title'] == 'Title'


def test_push_replaces_notification_with_same_id():
    store = _store()
    store.push(id='n1', title='Old', body='Old body')
    store.push(id='n1', title='New', body='New body')
    items = store.get_active()
    assert len(items) == 1
    assert items[0]['title'] == 'New'


def test_remove_existing_notification():
    store = _store()
    store.push(id='n1', title='Title', body='Body')
    removed = store.remove('n1')
    assert removed is True
    assert store.get_active() == []


def test_remove_nonexistent_returns_false():
    store = _store()
    removed = store.remove('does_not_exist')
    assert removed is False


def test_clear_removes_all():
    store = _store()
    store.push(id='n1', title='A', body='B')
    store.push(id='n2', title='C', body='D')
    store.clear()
    assert store.get_active() == []
    assert len(store) == 0


def test_push_multiple_notifications():
    store = _store()
    store.push(id='n1', title='T1', body='B1', severity='warning', type='persistent')
    store.push(id='n2', title='T2', body='B2', severity='info', type='informational')
    assert len(store) == 2
    ids = [n['id'] for n in store.get_active()]
    assert 'n1' in ids
    assert 'n2' in ids


def test_get_active_returns_snapshot():
    """Modifying the returned list should not affect the store."""
    store = _store()
    store.push(id='n1', title='T', body='B')
    snapshot = store.get_active()
    snapshot.clear()
    assert len(store) == 1
