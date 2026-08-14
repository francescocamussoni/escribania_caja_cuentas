from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_security_event
from app.core.security import (
    INVALID_CREDENTIALS_MESSAGE,
    create_access_token,
    verify_password,
)
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import (
    ChangePasswordAuthenticatedRequest,
    ChangePasswordPublicRequest,
    LoginRequest,
    LoginResponse,
)
from app.services.auth_service import (
    InvalidCredentialsError,
    PasswordUnchangedError,
    change_password,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    user = db.scalar(select(Usuario).where(Usuario.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        log_security_event(
            logger,
            "auth_login_failed",
            username=payload.username,
            reason="invalid_credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE,
        )

    access_token, expires_in = create_access_token(user.username, user.rol)
    log_security_event(
        logger,
        "auth_login_success",
        username=user.username,
        rol=user.rol,
    )
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        rol=user.rol,
    )


def _change_password_or_raise(
    db: Session,
    *,
    username: str,
    current_password: str,
    new_password: str,
) -> Usuario:
    try:
        return change_password(
            db,
            username=username,
            current_password=current_password,
            new_password=new_password,
        )
    except InvalidCredentialsError:
        log_security_event(
            logger,
            "password_change_failed",
            username=username,
            reason="invalid_credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE,
        ) from None
    except PasswordUnchangedError:
        log_security_event(
            logger,
            "password_change_failed",
            username=username,
            reason="password_unchanged",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La nueva contraseña debe ser distinta de la actual",
        ) from None


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password_public(
    payload: ChangePasswordPublicRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    user = _change_password_or_raise(
        db,
        username=payload.username,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    db.commit()
    log_security_event(
        logger,
        "password_change_success",
        username=user.username,
        rol=user.rol,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password_me(
    payload: ChangePasswordAuthenticatedRequest,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    user = _change_password_or_raise(
        db,
        username=current_user.username,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    db.commit()
    log_security_event(
        logger,
        "password_change_success",
        username=user.username,
        rol=user.rol,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
