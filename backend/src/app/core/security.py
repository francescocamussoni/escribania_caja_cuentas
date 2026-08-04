import bcrypt
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
INVALID_CREDENTIALS_MESSAGE = "Credenciales inválidas"
UNAUTHORIZED_MESSAGE = "No autenticado o token expirado"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(subject: str, rol: str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.jwt_expire_hours * 3600
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {"sub": subject, "rol": rol, "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict[str, str]:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    subject = payload.get("sub")
    rol = payload.get("rol")
    if not subject or not rol:
        raise JWTError("Invalid token payload")
    return {"sub": str(subject), "rol": str(rol)}
