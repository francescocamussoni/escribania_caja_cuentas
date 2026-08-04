from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_security_event
from app.core.security import (
    INVALID_CREDENTIALS_MESSAGE,
    create_access_token,
    verify_password,
)
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, LoginResponse

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
