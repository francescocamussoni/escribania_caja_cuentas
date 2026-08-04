from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_security_event
from app.core.security import (
    INVALID_CREDENTIALS_MESSAGE,
    UNAUTHORIZED_MESSAGE,
    decode_access_token,
)
from app.db.session import get_db
from app.models.usuario import Usuario

security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    if credentials is None:
        log_security_event(logger, "auth_failed", reason="missing_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHORIZED_MESSAGE,
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        log_security_event(logger, "auth_failed", reason="invalid_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHORIZED_MESSAGE,
        ) from None

    user = db.scalar(select(Usuario).where(Usuario.username == payload["sub"]))
    if user is None:
        log_security_event(logger, "auth_failed", reason="user_not_found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHORIZED_MESSAGE,
        )
    return user


def require_role(*roles: str):
    def _require_role(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> Usuario:
        if current_user.rol not in roles:
            log_security_event(
                logger,
                "auth_forbidden",
                username=current_user.username,
                rol=current_user.rol,
                required_roles=list(roles),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para realizar esta acción",
            )
        return current_user

    return _require_role
