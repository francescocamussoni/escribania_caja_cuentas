"""Operaciones de alta y reset de usuarios (uso operativo, no API)."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.usuario import Usuario

ALLOWED_ROLES = frozenset({"secretaria", "escribano"})
MAX_USERNAME_LENGTH = 50


class UserOpsError(ValueError):
    """Error de validación o estado en alta/reset de usuario."""


def validate_username(username: str) -> str:
    cleaned = username.strip()
    if not cleaned or len(cleaned) > MAX_USERNAME_LENGTH:
        raise UserOpsError(
            f"username debe tener entre 1 y {MAX_USERNAME_LENGTH} caracteres"
        )
    return cleaned


def validate_role(rol: str) -> str:
    cleaned = rol.strip()
    if cleaned not in ALLOWED_ROLES:
        allowed = ", ".join(sorted(ALLOWED_ROLES))
        raise UserOpsError(f"rol debe ser uno de: {allowed}")
    return cleaned


def validate_password(password: str) -> str:
    if password == "":
        raise UserOpsError("la contraseña no puede estar vacía")
    return password


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    rol: str,
) -> Usuario:
    username = validate_username(username)
    rol = validate_role(rol)
    password = validate_password(password)

    existing = db.scalar(select(Usuario).where(Usuario.username == username))
    if existing is not None:
        raise UserOpsError(f"Usuario {username} ya existe")

    user = Usuario(
        username=username,
        password_hash=hash_password(password),
        rol=rol,
    )
    db.add(user)
    db.flush()
    return user


def reset_user_password(
    db: Session,
    *,
    username: str,
    password: str,
) -> Usuario:
    username = validate_username(username)
    password = validate_password(password)

    user = db.scalar(select(Usuario).where(Usuario.username == username))
    if user is None:
        raise UserOpsError(f"Usuario {username} no encontrado")

    user.password_hash = hash_password(password)
    user.password_changed_at = datetime.now(timezone.utc)
    db.flush()
    return user
