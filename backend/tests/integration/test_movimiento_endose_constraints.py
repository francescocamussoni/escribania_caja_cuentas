"""
T003 (parte DB) — TDD: CHECK constraints e índice único del endose (feature 011).

  - ck_movimiento_endose_cheque
  - ck_movimiento_endose_destino
  - uq_movimiento_endose_cheque

Cada intento inválido debe ser rechazado por la base de datos (IntegrityError).
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
NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def user_id(db_session: Session) -> int:
    user = db_session.scalar(select(Usuario).where(Usuario.username == "admin"))
    assert user is not None
    return user.id


@pytest.fixture
def cajas(db_session: Session) -> tuple[int, int]:
    ebel = db_session.scalar(select(Caja).where(Caja.slug == "ebel"))
    martin = db_session.scalar(select(Caja).where(Caja.slug == "martin"))
    assert ebel is not None and martin is not None
    return ebel.id, martin.id


def _insert(db_session: Session, caja_id: int, user_id: int, **kwargs) -> Movimiento:
    base = dict(
        caja_id=caja_id,
        descripcion="endose constraint test",
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


def _insert_cheque_liquidado(db_session, caja_id, user_id, **kwargs) -> Movimiento:
    return _insert(
        db_session,
        caja_id,
        user_id,
        instrumento="cheque",
        fecha_liquidacion=FUTURE,
        fecha_liquidado=NOW,
        **kwargs,
    )


def test_cheque_liquidado_con_endose_es_aceptado(db_session, cajas, user_id) -> None:
    origen, destino = cajas
    mov = _insert_cheque_liquidado(db_session, origen, user_id, endosado_a_caja_id=destino)
    assert mov.endosado_a_caja_id == destino


def test_endosado_a_caja_en_movimiento_comun_es_rechazado(db_session, cajas, user_id) -> None:
    origen, destino = cajas
    with pytest.raises(IntegrityError):
        _insert(db_session, origen, user_id, endosado_a_caja_id=destino)


def test_endosado_a_caja_en_cheque_pendiente_es_rechazado(db_session, cajas, user_id) -> None:
    origen, destino = cajas
    with pytest.raises(IntegrityError):
        _insert(
            db_session,
            origen,
            user_id,
            instrumento="cheque",
            fecha_liquidacion=FUTURE,
            subtotal=None,
            endosado_a_caja_id=destino,
        )


def test_endose_cheque_id_en_movimiento_comun_es_aceptado(db_session, cajas, user_id) -> None:
    origen, destino = cajas
    cheque = _insert_cheque_liquidado(db_session, origen, user_id, endosado_a_caja_id=destino)
    destino_mov = _insert(
        db_session, destino, user_id, tipo="salida", endose_cheque_id=cheque.id
    )
    assert destino_mov.endose_cheque_id == cheque.id


def test_endose_cheque_id_en_un_cheque_es_rechazado(db_session, cajas, user_id) -> None:
    origen, destino = cajas
    cheque = _insert_cheque_liquidado(db_session, origen, user_id, endosado_a_caja_id=destino)
    with pytest.raises(IntegrityError):
        _insert_cheque_liquidado(db_session, destino, user_id, endose_cheque_id=cheque.id)


def test_un_cheque_no_puede_originar_dos_movimientos_de_endose(
    db_session, cajas, user_id
) -> None:
    origen, destino = cajas
    cheque = _insert_cheque_liquidado(db_session, origen, user_id, endosado_a_caja_id=destino)
    _insert(db_session, destino, user_id, tipo="salida", endose_cheque_id=cheque.id)
    with pytest.raises(IntegrityError):
        _insert(db_session, destino, user_id, tipo="salida", endose_cheque_id=cheque.id)
