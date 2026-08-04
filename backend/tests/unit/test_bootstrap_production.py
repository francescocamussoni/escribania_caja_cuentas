import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.bootstrap_production import bootstrap_production
from app.catalog.cajas import CAJAS_CATALOG
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.seed import ESCRIBANO_USERNAME, run_seed


@pytest.fixture
def production_settings(monkeypatch) -> Settings:
    settings = Settings(
        database_url=get_settings().database_url,
        admin_username="prod-admin",
        admin_password="prod-secret-password",
        jwt_secret="test-secret-key-with-enough-length",
        environment="production",
    )
    get_settings.cache_clear()
    monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.seed.get_settings", lambda: settings)
    return settings


@pytest.fixture
def bootstrap_db(db_engine, production_settings):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.flush()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _bootstrap(session: Session) -> None:
    bootstrap_production(session, commit=False)


def test_bootstrap_production_seeds_fifteen_cajas(bootstrap_db) -> None:
    _bootstrap(bootstrap_db)

    cajas = bootstrap_db.scalars(select(Caja)).all()
    assert len(cajas) == len(CAJAS_CATALOG)


def test_bootstrap_production_creates_admin_user_only(
    bootstrap_db, production_settings
) -> None:
    _bootstrap(bootstrap_db)

    usuarios = bootstrap_db.scalars(select(Usuario)).all()
    assert len(usuarios) == 1
    assert usuarios[0].username == production_settings.admin_username
    assert usuarios[0].rol == "secretaria"


def test_bootstrap_production_does_not_create_escribano_user(bootstrap_db) -> None:
    _bootstrap(bootstrap_db)

    escribano = bootstrap_db.scalar(
        select(Usuario).where(Usuario.username == ESCRIBANO_USERNAME)
    )
    assert escribano is None


def test_bootstrap_production_never_calls_seed_escribano_user(
    bootstrap_db, production_settings
) -> None:
    with patch("app.seed.seed_escribano_user") as seed_escribano_user:
        bootstrap_production(bootstrap_db, commit=False)

    seed_escribano_user.assert_not_called()
    assert production_settings.environment == "production"


def test_bootstrap_production_leaves_movimientos_empty(bootstrap_db) -> None:
    _bootstrap(bootstrap_db)

    movimientos_count = bootstrap_db.scalar(select(func.count()).select_from(Movimiento))
    assert movimientos_count == 0


def test_bootstrap_production_is_idempotent(bootstrap_db, production_settings) -> None:
    _bootstrap(bootstrap_db)
    _bootstrap(bootstrap_db)

    cajas_count = bootstrap_db.scalar(select(func.count()).select_from(Caja))
    usuarios_count = bootstrap_db.scalar(select(func.count()).select_from(Usuario))

    assert cajas_count == len(CAJAS_CATALOG)
    assert usuarios_count == 1


def test_run_seed_raises_in_production(production_settings) -> None:
    with pytest.raises(RuntimeError, match="bootstrap_production"):
        run_seed()
