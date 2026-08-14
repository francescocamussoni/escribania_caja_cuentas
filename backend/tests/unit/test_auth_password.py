"""Unit tests for change_password (T009 — TDD)."""

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.usuario import Usuario
from app.services.auth_service import (
    InvalidCredentialsError,
    PasswordUnchangedError,
    change_password,
)


def _insert_user(db_session: Session, username: str, password: str) -> Usuario:
    user = Usuario(
        username=username,
        password_hash=hash_password(password),
        rol="escribano",
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_change_password_updates_hash_and_cutover(db_session: Session) -> None:
    user = _insert_user(db_session, "user_change_ok", "OldPass12")

    change_password(
        db_session,
        username="user_change_ok",
        current_password="OldPass12",
        new_password="NuevaClave1",
    )

    db_session.refresh(user)
    assert verify_password("NuevaClave1", user.password_hash)
    assert not verify_password("OldPass12", user.password_hash)
    assert user.password_changed_at is not None


def test_change_password_rejects_wrong_current(db_session: Session) -> None:
    _insert_user(db_session, "user_change_wrong", "OldPass12")

    with pytest.raises(InvalidCredentialsError):
        change_password(
            db_session,
            username="user_change_wrong",
            current_password="bad-password",
            new_password="NuevaClave1",
        )


def test_change_password_rejects_unknown_user(db_session: Session) -> None:
    with pytest.raises(InvalidCredentialsError):
        change_password(
            db_session,
            username="no-existe",
            current_password="cualquier",
            new_password="NuevaClave1",
        )


def test_change_password_rejects_same_as_current(db_session: Session) -> None:
    user = _insert_user(db_session, "user_change_same", "OldPass12")
    original_hash = user.password_hash

    with pytest.raises(PasswordUnchangedError):
        change_password(
            db_session,
            username="user_change_same",
            current_password="OldPass12",
            new_password="OldPass12",
        )

    db_session.refresh(user)
    assert user.password_hash == original_hash
    assert user.password_changed_at is None
