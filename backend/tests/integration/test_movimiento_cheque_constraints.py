"""
T003 (parte DB) — TDD: CHECK constraints de `movimiento` para cheques (feature 010).

  - ck_movimiento_instrumento
  - ck_movimiento_cheque_fechas
  - ck_movimiento_subtotal_estado

Cada intento inválido debe ser rechazado por la base de datos (IntegrityError),
sin depender de validaciones de aplicación.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario

FUTURE = date(2030, 1, 15)
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def user_id(db_session: Session) -> int:
    user = db_session.scalar(select(Usuario).where(Usuario.username == "admin"))
    assert user is not None
    return user.id


@pytest.fixture
def caja_id(db_session: Session) -> int:
    caja = db_session.scalar(select(Caja).where(Caja.slug == "ebel"))
    assert caja is not None
    return caja.id


def _insert(db_session: Session, caja_id: int, user_id: int, **kwargs) -> Movimiento:
    base = dict(
        caja_id=caja_id,
        descripcion="constraint test",
        monto=Decimal("10.00"),
        tipo="entrada",
        moneda="ARS",
        instrumento="ninguno",
        subtotal=Decimal("10.00"),
        created_by=user_id,
    )
    base.update(kwargs)
    mov = Movimiento(**base)
    db_session.add(mov)
    db_session.flush()
    return mov


def test_valid_common_movement_is_accepted(db_session, caja_id, user_id) -> None:
    mov = _insert(db_session, caja_id, user_id)
    assert mov.id is not None


def test_valid_pending_cheque_is_accepted(db_session, caja_id, user_id) -> None:
    mov = _insert(
        db_session,
        caja_id,
        user_id,
        instrumento="cheque",
        fecha_liquidacion=FUTURE,
        subtotal=None,
    )
    assert mov.id is not None
    assert mov.subtotal is None


def test_valid_liquidated_cheque_is_accepted(db_session, caja_id, user_id) -> None:
    mov = _insert(
        db_session,
        caja_id,
        user_id,
        instrumento="echeque",
        fecha_liquidacion=FUTURE,
        fecha_liquidado=NOW,
        subtotal=Decimal("10.00"),
    )
    assert mov.id is not None


def test_invalid_instrumento_is_rejected(db_session, caja_id, user_id) -> None:
    with pytest.raises(IntegrityError):
        _insert(db_session, caja_id, user_id, instrumento="pagare")


def test_cheque_without_fecha_liquidacion_is_rejected(db_session, caja_id, user_id) -> None:
    with pytest.raises(IntegrityError):
        _insert(db_session, caja_id, user_id, instrumento="cheque", subtotal=None)


def test_ninguno_with_fecha_liquidacion_is_rejected(db_session, caja_id, user_id) -> None:
    with pytest.raises(IntegrityError):
        _insert(db_session, caja_id, user_id, fecha_liquidacion=FUTURE)


def test_ninguno_with_fecha_liquidado_is_rejected(db_session, caja_id, user_id) -> None:
    with pytest.raises(IntegrityError):
        _insert(db_session, caja_id, user_id, fecha_liquidado=NOW)


def test_ninguno_with_null_subtotal_is_rejected(db_session, caja_id, user_id) -> None:
    with pytest.raises(IntegrityError):
        _insert(db_session, caja_id, user_id, subtotal=None)


def test_pending_cheque_with_subtotal_is_rejected(db_session, caja_id, user_id) -> None:
    with pytest.raises(IntegrityError):
        _insert(
            db_session,
            caja_id,
            user_id,
            instrumento="cheque",
            fecha_liquidacion=FUTURE,
            subtotal=Decimal("10.00"),
        )


def test_liquidated_cheque_without_subtotal_is_rejected(db_session, caja_id, user_id) -> None:
    with pytest.raises(IntegrityError):
        _insert(
            db_session,
            caja_id,
            user_id,
            instrumento="cheque",
            fecha_liquidacion=FUTURE,
            fecha_liquidado=NOW,
            subtotal=None,
        )
