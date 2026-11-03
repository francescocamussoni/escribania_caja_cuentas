from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.cajas import CAJAS_CATALOG
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
import app.models  # noqa: F401 — register models for create_all
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


# ---------------------------------------------------------------------------
# Fixtures compartidas por los tests de cheques (feature 010)
# ---------------------------------------------------------------------------


@pytest.fixture
async def secretaria_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def escribano_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": ESCRIBANO_USERNAME, "password": ESCRIBANO_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def fresh_caja(client: AsyncClient, secretaria_headers: dict[str, str]) -> dict:
    """Caja nueva y vacía por test: aísla los tests de datos que otros dejaron en la DB."""
    response = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": f"Cheques {uuid4().hex[:12]}"},
        headers=secretaria_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
