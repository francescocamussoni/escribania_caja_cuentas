"""
T003 — TDD: propiedades derivadas de `Movimiento` para cheques/echeques (feature 010).

Reglas (data-model.md §1.6):
  - es_cheque        = instrumento != 'ninguno'
  - estado_cheque    = None | 'pendiente' | 'liquidado'
  - impacta_saldo    = subtotal is not None
  - fecha_carga      = fecha_override or created_at
  - fecha_efectiva   = fecha_liquidado or fecha_override or created_at

Son tests de lógica pura: no requieren base de datos.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

import app.models  # noqa: F401 — registra todos los mappers
from app.models.movimiento import Movimiento

T_CREATED = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
T_OVERRIDE = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
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


def test_movimiento_comun_no_es_cheque() -> None:
    mov = _mov()
    assert mov.es_cheque is False
    assert mov.estado_cheque is None
    assert mov.impacta_saldo is True


@pytest.mark.parametrize("instrumento", ["cheque", "echeque"])
def test_cheque_pendiente(instrumento: str) -> None:
    mov = _mov(
        instrumento=instrumento,
        fecha_liquidacion=date(2026, 11, 1),
        subtotal=None,
    )
    assert mov.es_cheque is True
    assert mov.estado_cheque == "pendiente"
    assert mov.impacta_saldo is False


@pytest.mark.parametrize("instrumento", ["cheque", "echeque"])
def test_cheque_liquidado(instrumento: str) -> None:
    mov = _mov(
        instrumento=instrumento,
        fecha_liquidacion=date(2026, 11, 1),
        fecha_liquidado=T_LIQUIDADO,
        subtotal=Decimal("10.00"),
    )
    assert mov.es_cheque is True
    assert mov.estado_cheque == "liquidado"
    assert mov.impacta_saldo is True


def test_fecha_carga_usa_created_at_sin_override() -> None:
    assert _mov().fecha_carga == T_CREATED


def test_fecha_carga_prefiere_override() -> None:
    assert _mov(fecha_override=T_OVERRIDE).fecha_carga == T_OVERRIDE


def test_fecha_efectiva_movimiento_comun_igual_que_antes() -> None:
    assert _mov().fecha_efectiva == T_CREATED
    assert _mov(fecha_override=T_OVERRIDE).fecha_efectiva == T_OVERRIDE


def test_fecha_efectiva_cheque_liquidado_usa_fecha_liquidado() -> None:
    mov = _mov(
        instrumento="cheque",
        fecha_liquidacion=date(2026, 11, 1),
        fecha_override=T_OVERRIDE,
        fecha_liquidado=T_LIQUIDADO,
    )
    assert mov.fecha_carga == T_OVERRIDE
    assert mov.fecha_efectiva == T_LIQUIDADO


def test_fecha_efectiva_cheque_pendiente_es_fecha_de_carga() -> None:
    mov = _mov(
        instrumento="cheque",
        fecha_liquidacion=date(2026, 11, 1),
        subtotal=None,
    )
    assert mov.fecha_efectiva == T_CREATED
