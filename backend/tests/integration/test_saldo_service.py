"""
T005 — TDD: `saldo_service` (feature 010).

Regla: saldo de (caja, moneda) = SUM(entrada +monto / salida -monto) sobre los
movimientos con `subtotal IS NOT NULL` (los que impactan el saldo). Los cheques
pendientes (subtotal NULL) NUNCA suman.

Cada test trabaja sobre una caja nueva dentro de la transacción del test
(`db_session` hace rollback), por lo que es independiente de datos previos.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.services.saldo_service import (
    get_saldo_actual,
    get_saldos_caja,
    get_saldos_cajas,
)

FUTURE = date(2030, 1, 15)
NOW = datetime.now(timezone.utc)


@pytest.fixture
def user(db_session: Session) -> Usuario:
    u = db_session.scalar(select(Usuario).where(Usuario.username == "admin"))
    assert u is not None
    return u


@pytest.fixture
def caja(db_session: Session) -> Caja:
    suffix = uuid4().hex[:10]
    c = Caja(nombre=f"Saldo {suffix}", slug=f"saldo-{suffix}", estado="activa")
    db_session.add(c)
    db_session.flush()
    return c


def _add(
    db: Session,
    caja: Caja,
    user: Usuario,
    *,
    tipo: str,
    monto: str,
    moneda: str = "ARS",
    subtotal: str | None,
    instrumento: str = "ninguno",
    fecha_liquidacion: date | None = None,
    fecha_liquidado: datetime | None = None,
    fecha_override: datetime | None = None,
    created_at: datetime | None = None,
) -> Movimiento:
    mov = Movimiento(
        caja_id=caja.id,
        descripcion="saldo test",
        monto=Decimal(monto),
        tipo=tipo,
        moneda=moneda,
        subtotal=Decimal(subtotal) if subtotal is not None else None,
        instrumento=instrumento,
        fecha_liquidacion=fecha_liquidacion,
        fecha_liquidado=fecha_liquidado,
        fecha_override=fecha_override,
        created_by=user.id,
        **({"created_at": created_at} if created_at else {}),
    )
    db.add(mov)
    db.flush()
    return mov


def test_empty_caja_has_zero_saldo(db_session: Session, caja: Caja) -> None:
    assert get_saldo_actual(db_session, caja.id, "ARS") == Decimal("0.00")
    assert get_saldo_actual(db_session, caja.id, "USD") == Decimal("0.00")
    assert get_saldos_caja(db_session, caja.id) == (Decimal("0.00"), Decimal("0.00"))


def test_saldo_is_sum_of_entradas_minus_salidas(
    db_session: Session, caja: Caja, user: Usuario
) -> None:
    _add(db_session, caja, user, tipo="entrada", monto="1000.00", subtotal="1000.00")
    _add(db_session, caja, user, tipo="salida", monto="300.00", subtotal="700.00")
    _add(db_session, caja, user, tipo="entrada", monto="50.50", subtotal="750.50")

    assert get_saldo_actual(db_session, caja.id, "ARS") == Decimal("750.50")


def test_saldo_equals_last_subtotal_on_consistent_stream(
    db_session: Session, caja: Caja, user: Usuario
) -> None:
    movs = [
        _add(db_session, caja, user, tipo="entrada", monto="200.00", subtotal="200.00"),
        _add(db_session, caja, user, tipo="entrada", monto="100.00", subtotal="300.00"),
        _add(db_session, caja, user, tipo="salida", monto="40.00", subtotal="260.00"),
    ]
    assert get_saldo_actual(db_session, caja.id, "ARS") == movs[-1].subtotal


def test_pending_cheques_are_ignored(
    db_session: Session, caja: Caja, user: Usuario
) -> None:
    _add(db_session, caja, user, tipo="entrada", monto="1000.00", subtotal="1000.00")
    _add(
        db_session, caja, user,
        tipo="entrada", monto="500.00", subtotal=None,
        instrumento="cheque", fecha_liquidacion=FUTURE,
    )
    _add(
        db_session, caja, user,
        tipo="salida", monto="200.00", subtotal=None,
        instrumento="echeque", fecha_liquidacion=FUTURE,
    )

    assert get_saldo_actual(db_session, caja.id, "ARS") == Decimal("1000.00")


def test_liquidated_cheques_are_counted(
    db_session: Session, caja: Caja, user: Usuario
) -> None:
    _add(db_session, caja, user, tipo="entrada", monto="1000.00", subtotal="1000.00")
    _add(
        db_session, caja, user,
        tipo="entrada", monto="500.00", subtotal="1500.00",
        instrumento="cheque", fecha_liquidacion=FUTURE, fecha_liquidado=NOW,
    )
    _add(
        db_session, caja, user,
        tipo="salida", monto="200.00", subtotal="1300.00",
        instrumento="echeque", fecha_liquidacion=FUTURE, fecha_liquidado=NOW,
    )

    assert get_saldo_actual(db_session, caja.id, "ARS") == Decimal("1300.00")


def test_ars_and_usd_are_independent(
    db_session: Session, caja: Caja, user: Usuario
) -> None:
    _add(db_session, caja, user, tipo="entrada", monto="1000.00", moneda="ARS", subtotal="1000.00")
    _add(db_session, caja, user, tipo="entrada", monto="75.25", moneda="USD", subtotal="75.25")
    _add(
        db_session, caja, user,
        tipo="entrada", monto="999.00", moneda="USD", subtotal=None,
        instrumento="cheque", fecha_liquidacion=FUTURE,
    )

    assert get_saldos_caja(db_session, caja.id) == (Decimal("1000.00"), Decimal("75.25"))


def test_saldo_correct_with_past_fecha_override_and_stale_subtotals(
    db_session: Session, caja: Caja, user: Usuario
) -> None:
    """La suma no depende del orden ni de subtotales desactualizados."""
    past = NOW - timedelta(days=30)
    _add(db_session, caja, user, tipo="entrada", monto="100.00", subtotal="100.00")
    # Carga retroactiva con subtotal "viejo" (inconsistente a propósito)
    _add(
        db_session, caja, user,
        tipo="entrada", monto="50.00", subtotal="50.00", fecha_override=past,
    )

    assert get_saldo_actual(db_session, caja.id, "ARS") == Decimal("150.00")


def test_get_saldos_cajas_returns_entry_for_every_requested_caja(
    db_session: Session, caja: Caja, user: Usuario
) -> None:
    suffix = uuid4().hex[:10]
    otra = Caja(nombre=f"Otra {suffix}", slug=f"otra-{suffix}", estado="activa")
    db_session.add(otra)
    db_session.flush()
    _add(db_session, caja, user, tipo="entrada", monto="10.00", subtotal="10.00")

    result = get_saldos_cajas(db_session, [caja.id, otra.id])

    assert result[caja.id] == (Decimal("10.00"), Decimal("0.00"))
    assert result[otra.id] == (Decimal("0.00"), Decimal("0.00"))
