"""Unit tests for operational user create/reset."""

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.usuario import Usuario
from app.services.user_ops import (
    UserOpsError,
    create_user,
    reset_user_password,
)


def test_create_user_escribano(db_session: Session) -> None:
    user = create_user(
        db_session,
        username="juan.perez",
        password="ClaveSegura1",
        rol="escribano",
    )

    db_session.refresh(user)
    assert user.username == "juan.perez"
    assert user.rol == "escribano"
    assert verify_password("ClaveSegura1", user.password_hash)
    assert user.password_changed_at is None


def test_create_user_secretaria(db_session: Session) -> None:
    user = create_user(
        db_session,
        username="ana.secretaria",
        password="ClaveSegura1",
        rol="secretaria",
    )

    assert user.rol == "secretaria"


def test_create_user_rejects_duplicate(db_session: Session) -> None:
    create_user(
        db_session,
        username="dup.user",
        password="ClaveSegura1",
        rol="escribano",
    )

    with pytest.raises(UserOpsError, match="ya existe"):
        create_user(
            db_session,
            username="dup.user",
            password="OtraClave12",
            rol="escribano",
        )


def test_create_user_rejects_invalid_role(db_session: Session) -> None:
    with pytest.raises(UserOpsError, match="rol"):
        create_user(
            db_session,
            username="bad.rol",
            password="ClaveSegura1",
            rol="admin",
        )


def test_create_user_rejects_empty_password(db_session: Session) -> None:
    with pytest.raises(UserOpsError, match="contraseña"):
        create_user(
            db_session,
            username="empty.pass",
            password="",
            rol="escribano",
        )


def test_create_user_allows_short_password(db_session: Session) -> None:
    user = create_user(
        db_session,
        username="short.pass",
        password="ab",
        rol="escribano",
    )

    assert verify_password("ab", user.password_hash)


def test_create_user_rejects_blank_username(db_session: Session) -> None:
    with pytest.raises(UserOpsError, match="username"):
        create_user(
            db_session,
            username="  ",
            password="ClaveSegura1",
            rol="escribano",
        )


def test_reset_user_password_updates_hash_and_cutover(db_session: Session) -> None:
    user = Usuario(
        username="reset.user",
        password_hash=hash_password("ViejaClave1"),
        rol="escribano",
    )
    db_session.add(user)
    db_session.flush()

    reset_user_password(
        db_session,
        username="reset.user",
        password="NuevaClave1",
    )

    db_session.refresh(user)
    assert verify_password("NuevaClave1", user.password_hash)
    assert not verify_password("ViejaClave1", user.password_hash)
    assert user.password_changed_at is not None


def test_reset_user_password_missing_user(db_session: Session) -> None:
    with pytest.raises(UserOpsError, match="no encontrado"):
        reset_user_password(
            db_session,
            username="no.existe",
            password="ClaveSegura1",
        )
