from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.usuario import Usuario


class InvalidCredentialsError(Exception):
    """Usuario inexistente o contraseña actual incorrecta."""


class PasswordUnchangedError(Exception):
    """La nueva contraseña es igual a la actual."""


def change_password(
    db: Session,
    *,
    username: str,
    current_password: str,
    new_password: str,
) -> Usuario:
    user = db.scalar(select(Usuario).where(Usuario.username == username))
    if user is None or not verify_password(current_password, user.password_hash):
        raise InvalidCredentialsError()

    if current_password == new_password:
        raise PasswordUnchangedError()

    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    db.flush()
    return user
