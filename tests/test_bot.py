"""Bot access-control tests — the security filter must be airtight.

We avoid importing the full telegram stack objects and instead feed the pure
filter functions lightweight stand-ins that expose the same attributes.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.bot import handlers
from app.config import settings

GROUP_ID = "-1001234567890"
ADMIN_ID = "555000111"


def _update(chat_type, chat_id, user_id, is_bot=False):
    return SimpleNamespace(
        effective_chat=SimpleNamespace(type=chat_type, id=chat_id),
        effective_user=SimpleNamespace(id=user_id, is_bot=is_bot, username="u"),
    )


def _configure(monkeypatch):
    monkeypatch.setattr(settings, "telegram_group_id", GROUP_ID)
    monkeypatch.setattr(settings, "telegram_admin_id", ADMIN_ID)
    monkeypatch.setattr(settings, "group_id", "")
    monkeypatch.setattr(settings, "admin_id", "")


def test_group_message_in_configured_group_is_authorized(monkeypatch):
    _configure(monkeypatch)
    assert handlers._is_authorized(_update("supergroup", GROUP_ID, 42)) is True


def test_group_message_in_other_group_is_rejected(monkeypatch):
    _configure(monkeypatch)
    assert handlers._is_authorized(_update("supergroup", "-100999", 42)) is False


def test_private_admin_is_authorized(monkeypatch):
    _configure(monkeypatch)
    assert handlers._is_authorized(_update("private", ADMIN_ID, ADMIN_ID)) is True


def test_private_non_admin_is_rejected(monkeypatch):
    _configure(monkeypatch)
    assert handlers._is_authorized(_update("private", "999", "999")) is False


def test_messages_from_other_bots_are_ignored(monkeypatch):
    _configure(monkeypatch)
    assert handlers._is_authorized(_update("supergroup", GROUP_ID, 42, is_bot=True)) is False


def test_admin_check(monkeypatch):
    _configure(monkeypatch)
    assert handlers._is_admin(_update("supergroup", GROUP_ID, ADMIN_ID)) is True
    assert handlers._is_admin(_update("supergroup", GROUP_ID, "42")) is False
