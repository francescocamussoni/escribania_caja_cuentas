"""
T003 — TDD: propiedades derivadas de `Movimiento` para el endose de cheques (feature 011).

  - endosado               = endosado_a_caja_id is not None
  - es_endose_destino      = endose_cheque_id is not None
  - bloqueado_por_endose   = endosado or es_endose_destino

Tests de lógica pura: no requieren base de datos. Los CHECK y el índice único se prueban en
`tests/integration/test_movimiento_endose_constraints.py`.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import app.models  # noqa: F401 — registra todos los mappers
from app.models.movimiento import Movimiento

T_CREATED = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
T_LIQUIDADO = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)


def _mov(**kwargs) -> Movimiento:
    base = dict(
        caja_id=1,
        descripcion="x",
        monto=Decimal("10.00"),
        tipo="entrada",
        moneda="ARS",
        instrumento="ninguno",
        subtotal=Decimal("10.00"),
        created_at=T_CREATED,
        created_by=1,
    )
    base.update(kwargs)
    return Movimiento(**base)


def test_movimiento_comun_no_esta_bloqueado() -> None:
    mov = _mov()
    assert mov.endosado is False
    assert mov.es_endose_destino is False
    assert mov.bloqueado_por_endose is False


def test_cheque_pendiente_no_esta_bloqueado() -> None:
    mov = _mov(instrumento="cheque", fecha_liquidacion=date(2030, 1, 1), subtotal=None)
    assert mov.endosado is False
    assert mov.bloqueado_por_endose is False


def test_cheque_liquidado_sin_endose_no_esta_bloqueado() -> None:
    mov = _mov(
        instrumento="cheque",
        fecha_liquidacion=date(2030, 1, 1),
        fecha_liquidado=T_LIQUIDADO,
    )
    assert mov.endosado is False
    assert mov.bloqueado_por_endose is False


def test_cheque_endosado_esta_bloqueado() -> None:
    mov = _mov(
        instrumento="cheque",
        fecha_liquidacion=date(2030, 1, 1),
        fecha_liquidado=T_LIQUIDADO,
        endosado_a_caja_id=2,
    )
    assert mov.endosado is True
    assert mov.es_endose_destino is False
    assert mov.bloqueado_por_endose is True
    # Sigue siendo un cheque liquidado (no hay un tercer estado).
    assert mov.estado_cheque == "liquidado"


def test_movimiento_de_endose_esta_bloqueado() -> None:
    mov = _mov(endose_cheque_id=99)
    assert mov.endosado is False
    assert mov.es_endose_destino is True
    assert mov.bloqueado_por_endose is True
