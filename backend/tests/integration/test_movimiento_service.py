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


# ---------------------------------------------------------------------------
# T007 — feature 010: stream con cheques (DB real, caja aislada por test)
# ---------------------------------------------------------------------------

from datetime import date, datetime, timedelta, timezone  # noqa: E402
from uuid import uuid4  # noqa: E402


@pytest.fixture
def caja_aislada(db_session: Session) -> Caja:
    suffix = uuid4().hex[:10]
    caja = Caja(nombre=f"Stream {suffix}", slug=f"stream-{suffix}", estado="activa")
    db_session.add(caja)
    db_session.flush()
    return caja


def _insert_cheque_pendiente(db: Session, caja: Caja, user: Usuario, monto: str) -> Movimiento:
    mov = Movimiento(
        caja_id=caja.id,
        descripcion="cheque pendiente",
        monto=Decimal(monto),
        tipo="entrada",
        moneda="ARS",
        instrumento="cheque",
        fecha_liquidacion=date(2030, 1, 1),
        subtotal=None,
        created_by=user.id,
    )
    db.add(mov)
    db.flush()
    return mov


def test_pending_cheque_does_not_affect_next_subtotal(
    movimiento_service: MovimientoService,
    caja_aislada: Caja,
    secretaria_user: Usuario,
    db_session: Session,
) -> None:
    movimiento_service.create_movimiento(
        caja_id=caja_aislada.id, descripcion="base", monto=Decimal("100.00"),
        tipo="entrada", user=secretaria_user,
    )
    cheque = _insert_cheque_pendiente(db_session, caja_aislada, secretaria_user, "500.00")

    siguiente = movimiento_service.create_movimiento(
        caja_id=caja_aislada.id, descripcion="despues", monto=Decimal("10.00"),
        tipo="salida", user=secretaria_user,
    )

    assert siguiente.subtotal == Decimal("90.00")
    assert cheque.subtotal is None


def test_recalculate_skips_pending_cheques(
    movimiento_service: MovimientoService,
    caja_aislada: Caja,
    secretaria_user: Usuario,
    db_session: Session,
) -> None:
    movimiento_service.create_movimiento(
        caja_id=caja_aislada.id, descripcion="base", monto=Decimal("100.00"),
        tipo="entrada", user=secretaria_user,
    )
    cheque = _insert_cheque_pendiente(db_session, caja_aislada, secretaria_user, "500.00")

    movimiento_service.recalculate_subtotals(caja_aislada.id, moneda="ARS")
    db_session.refresh(cheque)

    assert cheque.subtotal is None


def test_create_with_past_fecha_override_recalculates_later_subtotals(
    movimiento_service: MovimientoService,
    caja_aislada: Caja,
    secretaria_user: Usuario,
    db_session: Session,
) -> None:
    reciente = movimiento_service.create_movimiento(
        caja_id=caja_aislada.id, descripcion="hoy", monto=Decimal("100.00"),
        tipo="entrada", user=secretaria_user,
    )
    retro = movimiento_service.create_movimiento(
        caja_id=caja_aislada.id, descripcion="retro", monto=Decimal("50.00"),
        tipo="entrada", fecha_override=datetime.now(timezone.utc) - timedelta(days=30),
        user=secretaria_user,
    )
    db_session.refresh(reciente)

    assert retro.subtotal == Decimal("50.00")  # primero en el orden cronológico
    assert reciente.subtotal == Decimal("150.00")  # recalculado en cascada


def test_stream_orders_liquidated_cheque_by_fecha_liquidado(
    movimiento_service: MovimientoService,
    caja_aislada: Caja,
    secretaria_user: Usuario,
    db_session: Session,
) -> None:
    """Un cheque liquidado ahora queda DESPUÉS de un movimiento común cargado antes."""
    base = movimiento_service.create_movimiento(
        caja_id=caja_aislada.id, descripcion="base", monto=Decimal("100.00"),
        tipo="entrada", user=secretaria_user,
    )
    cheque = Movimiento(
        caja_id=caja_aislada.id, descripcion="cheque", monto=Decimal("40.00"),
        tipo="salida", moneda="ARS", instrumento="cheque",
        fecha_liquidacion=date(2030, 1, 1),
        created_at=datetime.now(timezone.utc) - timedelta(days=10),  # cargado hace tiempo
        fecha_liquidado=datetime.now(timezone.utc),                  # liquidado ahora
        subtotal=Decimal("0.00"),
        created_by=secretaria_user.id,
    )
    db_session.add(cheque)
    db_session.flush()

    movimiento_service.recalculate_subtotals(caja_aislada.id, moneda="ARS")
    db_session.refresh(base)
    db_session.refresh(cheque)

    assert base.subtotal == Decimal("100.00")
    assert cheque.subtotal == Decimal("60.00")


def test_update_moneda_replays_moved_row_in_its_new_stream(
    db_session: Session,
    caja_aislada: Caja,
    secretaria_user: Usuario,
) -> None:
    """Regression: with autoflush disabled, the moved row kept a stale subtotal."""
    from sqlalchemy.orm import sessionmaker

    # Mimic production sessions (autoflush=False), sharing the test transaction.
    session = sessionmaker(bind=db_session.get_bind(), autoflush=False)()
    try:
        service = MovimientoService(session)
        ars = service.create_movimiento(
            caja_id=caja_aislada.id, descripcion="ars", monto=Decimal("500.00"),
            tipo="entrada", moneda="ARS", user=secretaria_user,
        )
        usd = service.create_movimiento(
            caja_id=caja_aislada.id, descripcion="usd", monto=Decimal("200.00"),
            tipo="entrada", moneda="USD", user=secretaria_user,
        )

        service.update_movimiento(
            caja_id=caja_aislada.id, movimiento_id=ars.id, user=secretaria_user, moneda="USD",
        )
        session.refresh(ars)
        session.refresh(usd)

        # ARS (500) was created first, so it opens the USD stream: 500 then 700.
        assert ars.subtotal == Decimal("500.00")
        assert usd.subtotal == Decimal("700.00")
    finally:
        session.rollback()
        session.close()
