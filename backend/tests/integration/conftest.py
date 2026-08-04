import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.cajas import CAJAS_CATALOG
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.models.caja import Caja
from app.models.usuario import Usuario
from app.seed import seed_cajas

ESCRIBANO_USERNAME = "escribano"
ESCRIBANO_PASSWORD = "escribano"


@pytest.fixture(scope="session", autouse=True)
def prepare_auth_database(db_engine) -> None:
    Base.metadata.create_all(bind=db_engine)

    settings = get_settings()
    with Session(bind=db_engine) as session:
        admin = session.scalar(
            select(Usuario).where(Usuario.username == settings.admin_username)
        )
        if admin is None:
            session.add(
                Usuario(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    rol="secretaria",
                )
            )

        escribano = session.scalar(
            select(Usuario).where(Usuario.username == ESCRIBANO_USERNAME)
        )
        if escribano is None:
            session.add(
                Usuario(
                    username=ESCRIBANO_USERNAME,
                    password_hash=hash_password(ESCRIBANO_PASSWORD),
                    rol="escribano",
                )
            )

        session.flush()
        seed_cajas(session)
        session.commit()
