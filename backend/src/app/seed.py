from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.cajas import CAJAS_CATALOG
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.caja import Caja
from app.models.usuario import Usuario


ESCRIBANO_USERNAME = "escribano"
ESCRIBANO_PASSWORD = "escribano"


def seed_admin_user(db: Session) -> None:
    settings = get_settings()
    existing = db.scalar(
        select(Usuario).where(Usuario.username == settings.admin_username)
    )
    if existing is not None:
        return

    db.add(
        Usuario(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            rol="secretaria",
        )
    )


def seed_escribano_user(db: Session) -> None:
    existing = db.scalar(select(Usuario).where(Usuario.username == ESCRIBANO_USERNAME))
    if existing is not None:
        return

    db.add(
        Usuario(
            username=ESCRIBANO_USERNAME,
            password_hash=hash_password(ESCRIBANO_PASSWORD),
            rol="escribano",
        )
    )


def seed_cajas(db: Session) -> None:
    """Insert the 15 initial activas from CAJAS_CATALOG if those slugs are missing.

    Does not replace or constrain the live list: secretaria altas persist via
    the API without editing this catalog. Existing rows are left unchanged
    (including archivadas).
    """
    for item in CAJAS_CATALOG:
        existing = db.scalar(select(Caja).where(Caja.slug == item["slug"]))
        if existing is not None:
            continue
        db.add(Caja(nombre=item["nombre"], slug=item["slug"]))


def run_seed() -> None:
    settings = get_settings()
    if settings.environment.lower() == "production":
        raise RuntimeError(
            "run_seed() must not be used in production; use bootstrap_production"
        )

    db = SessionLocal()
    try:
        seed_admin_user(db)
        seed_escribano_user(db)
        seed_cajas(db)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
