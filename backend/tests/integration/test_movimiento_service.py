from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.services.movimiento_service import MovimientoService


@pytest.fixture
def movimiento_service(db_session: Session) -> MovimientoService:
    return MovimientoService(db_session)


@pytest.fixture
def caja_ebel(db_session: Session) -> Caja:
    caja = db_session.scalar(select(Caja).where(Caja.slug == "ebel"))
    assert caja is not None
    return caja


@pytest.fixture
def secretaria_user(db_session: Session) -> Usuario:
    user = db_session.scalar(select(Usuario).where(Usuario.username == "admin"))
    assert user is not None
    return user


def _previous_subtotal(db_session: Session, caja_id: int) -> Decimal:
    last_movimiento = db_session.scalar(
        select(Movimiento)
        .where(Movimiento.caja_id == caja_id)
        .order_by(Movimiento.created_at.desc(), Movimiento.id.desc())
    )
    return last_movimiento.subtotal if last_movimiento else Decimal("0")


def test_create_first_entrada_sets_subtotal(
    movimiento_service: MovimientoService,
    caja_ebel: Caja,
    secretaria_user: Usuario,
    db_session: Session,
) -> None:
    previous = _previous_subtotal(db_session, caja_ebel.id)
    movimiento = movimiento_service.create_movimiento(
        caja_id=caja_ebel.id,
        descripcion="Pago cliente",
        monto=Decimal("5000.00"),
        tipo="entrada",
        user=secretaria_user,
    )

    assert movimiento.subtotal == previous + Decimal("5000.00")
    assert movimiento.tipo == "entrada"


def test_create_salida_after_entrada_updates_subtotal(
    movimiento_service: MovimientoService,
    caja_ebel: Caja,
    secretaria_user: Usuario,
    db_session: Session,
) -> None:
    previous = _previous_subtotal(db_session, caja_ebel.id)
    movimiento_service.create_movimiento(
        caja_id=caja_ebel.id,
        descripcion="Cobro inicial",
        monto=Decimal("10000.00"),
        tipo="entrada",
        user=secretaria_user,
    )
    salida = movimiento_service.create_movimiento(
        caja_id=caja_ebel.id,
        descripcion="Pago proveedor",
        monto=Decimal("3000.00"),
        tipo="salida",
        user=secretaria_user,
    )

    assert salida.subtotal == previous + Decimal("7000.00")


def test_create_movimiento_commits_in_transaction(
    movimiento_service: MovimientoService,
    caja_ebel: Caja,
    secretaria_user: Usuario,
    db_session: Session,
) -> None:
    previous = _previous_subtotal(db_session, caja_ebel.id)
    movimiento = movimiento_service.create_movimiento(
        caja_id=caja_ebel.id,
        descripcion="Depósito",
        monto=Decimal("100.00"),
        tipo="entrada",
        user=secretaria_user,
    )

    persisted = db_session.get(type(movimiento), movimiento.id)
    assert persisted is not None
    assert persisted.subtotal == previous + Decimal("100.00")
