from datetime import datetime, timedelta, timezone

from app.infrastructure.firestore.ttl import (
    ATTEMPT_AND_HINT_RETENTION,
    RATE_LIMIT_RETENTION,
    expire_at,
)


def test_expire_at_adds_retention_to_base():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert expire_at(base, timedelta(days=10)) == datetime(2026, 1, 11, tzinfo=timezone.utc)


def test_expire_at_returns_none_for_none_base():
    assert expire_at(None, timedelta(days=10)) is None


def test_attempt_and_hint_retention_is_180_days():
    assert ATTEMPT_AND_HINT_RETENTION == timedelta(days=180)


def test_rate_limit_retention_is_7_days():
    assert RATE_LIMIT_RETENTION == timedelta(days=7)
