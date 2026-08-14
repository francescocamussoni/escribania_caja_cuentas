"""Unit tests for JWT iat vs usuario.password_changed_at (T004 — TDD)."""

from datetime import datetime, timedelta, timezone

from app.core.security import (
    create_access_token,
    decode_access_token,
    is_access_token_revoked_by_password_change,
)


def test_null_password_changed_at_does_not_revoke_token_without_iat() -> None:
    assert (
        is_access_token_revoked_by_password_change(iat=None, password_changed_at=None)
        is False
    )


def test_null_password_changed_at_does_not_revoke_token_with_iat() -> None:
    now = datetime.now(timezone.utc)
    assert (
        is_access_token_revoked_by_password_change(
            iat=int(now.timestamp()),
            password_changed_at=None,
        )
        is False
    )


def test_iat_before_password_change_is_revoked() -> None:
    changed = datetime.now(timezone.utc)
    iat = int((changed - timedelta(minutes=5)).timestamp())
    assert (
        is_access_token_revoked_by_password_change(
            iat=iat,
            password_changed_at=changed,
        )
        is True
    )


def test_iat_same_second_before_change_is_revoked() -> None:
    changed = datetime(2026, 8, 14, 13, 5, 8, 80000, tzinfo=timezone.utc)
    iat = int(changed.timestamp())
    assert (
        is_access_token_revoked_by_password_change(
            iat=iat,
            password_changed_at=changed,
        )
        is True
    )


def test_fractional_iat_after_password_change_is_accepted() -> None:
    changed = datetime(2026, 8, 14, 13, 5, 8, 80000, tzinfo=timezone.utc)
    iat = changed.timestamp() + 0.1
    assert (
        is_access_token_revoked_by_password_change(
            iat=iat,
            password_changed_at=changed,
        )
        is False
    )


def test_iat_after_password_change_is_accepted() -> None:
    changed = datetime.now(timezone.utc) - timedelta(minutes=5)
    iat = int(datetime.now(timezone.utc).timestamp())
    assert (
        is_access_token_revoked_by_password_change(
            iat=iat,
            password_changed_at=changed,
        )
        is False
    )


def test_missing_iat_is_revoked_after_password_change() -> None:
    changed = datetime.now(timezone.utc)
    assert (
        is_access_token_revoked_by_password_change(
            iat=None,
            password_changed_at=changed,
        )
        is True
    )


def test_create_access_token_includes_iat_claim() -> None:
    token, expires_in = create_access_token("admin", "secretaria")
    payload = decode_access_token(token)
    assert payload["sub"] == "admin"
    assert payload["rol"] == "secretaria"
    assert isinstance(payload["iat"], (int, float))
    assert payload["iat"] > 0
    assert expires_in == 28800
