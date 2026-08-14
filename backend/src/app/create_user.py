"""CLI operativo: alta o reset de usuario contra la BD del contenedor.

La contraseña se lee por prompt (TTY) o por stdin (una línea). No usar --password.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from app.core.logging import get_logger, log_security_event
from app.db.session import SessionLocal
from app.services.user_ops import (
    ALLOWED_ROLES,
    UserOpsError,
    create_user,
    reset_user_password,
    validate_password,
    validate_role,
    validate_username,
)

logger = get_logger(__name__)


def _read_password(*, confirm: bool) -> str:
    if sys.stdin.isatty():
        password = getpass.getpass("Contraseña: ")
        if confirm:
            repeated = getpass.getpass("Confirmar contraseña: ")
            if password != repeated:
                raise UserOpsError("Las contraseñas no coinciden")
        return password
    line = sys.stdin.readline()
    if not line:
        raise UserOpsError("No se recibió contraseña por stdin")
    return line.rstrip("\n")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Crear un usuario o resetear su contraseña. "
            "La clave se pide de forma interactiva o por stdin."
        )
    )
    parser.add_argument("--username", required=True, help="Nombre de usuario (1–50)")
    parser.add_argument(
        "--rol",
        choices=sorted(ALLOWED_ROLES),
        help="Rol (obligatorio al crear; se ignora en --reset)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Actualizar la contraseña de un usuario existente (invalida sesiones JWT)",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        username = validate_username(args.username)
        if args.reset:
            password = validate_password(_read_password(confirm=sys.stdin.isatty()))
        else:
            if not args.rol:
                raise UserOpsError("--rol es obligatorio al crear un usuario")
            rol = validate_role(args.rol)
            password = validate_password(_read_password(confirm=sys.stdin.isatty()))
    except UserOpsError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        if args.reset:
            user = reset_user_password(db, username=username, password=password)
            db.commit()
            log_security_event(
                logger,
                "user_password_reset",
                username=user.username,
                rol=user.rol,
            )
            print(f"Contraseña actualizada para {user.username}")
            return 0

        user = create_user(
            db,
            username=username,
            password=password,
            rol=rol,
        )
        db.commit()
        log_security_event(
            logger,
            "user_created",
            username=user.username,
            rol=user.rol,
        )
        print(f"Usuario {user.username} creado ({user.rol})")
        return 0
    except UserOpsError as exc:
        db.rollback()
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        db.rollback()
        print("No se pudo completar la operación", file=sys.stderr)
        logger.exception("user_ops_failed")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run())
