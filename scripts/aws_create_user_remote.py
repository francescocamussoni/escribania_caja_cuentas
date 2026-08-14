"""Runs inside the production API container. Password via env, never printed."""

import os
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.usuario import Usuario

username = os.environ["CREATE_USER_USERNAME"]
mode = os.environ["CREATE_USER_MODE"]
password = os.environ["CREATE_USER_PASSWORD"]
rol = os.environ.get("CREATE_USER_ROL") or ""

if password == "":
    print("la contraseña no puede estar vacía", file=sys.stderr)
    raise SystemExit(2)

db = SessionLocal()
try:
    user = db.scalar(select(Usuario).where(Usuario.username == username))
    if mode == "reset":
        if user is None:
            print(f"Usuario {username} no encontrado", file=sys.stderr)
            raise SystemExit(1)
        user.password_hash = hash_password(password)
        if hasattr(user, "password_changed_at"):
            user.password_changed_at = datetime.now(timezone.utc)
        db.commit()
        print(f"Contraseña actualizada para {username}")
    else:
        if user is not None:
            print(f"Usuario {username} ya existe", file=sys.stderr)
            raise SystemExit(1)
        if rol not in {"secretaria", "escribano"}:
            print("rol inválido", file=sys.stderr)
            raise SystemExit(2)
        db.add(
            Usuario(
                username=username,
                password_hash=hash_password(password),
                rol=rol,
            )
        )
        db.commit()
        print(f"Usuario {username} creado ({rol})")
finally:
    db.close()
