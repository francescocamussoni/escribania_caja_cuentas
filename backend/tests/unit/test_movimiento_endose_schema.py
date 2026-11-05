"""
T010 — TDD: schemas del endose (feature 011, US1).

  - EndosarChequeRequest: caja_destino_id obligatorio, entero >= 1, extra="forbid"
  - MovimientoResponse: endosable / endosado_a / endose_origen / editable
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

import app.models  # noqa: F401
from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.schemas.movimiento import EndosarChequeRequest, movimiento_to_response

T_CREATED = datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc)
T_LIQUIDADO = datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)

CAJA_A = Caja(id=3, nombre="Ebel", slug="ebel", estado="activa")
CAJA_B = Caja(id=4, nombre="Martin", slug="martin", estado="activa")


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


def test_request_accepts_a_valid_caja_destino_id() -> None:
    assert EndosarChequeRequest(caja_destino_id=4).caja_destino_id == 4


@pytest.mark.parametrize("value", [0, -1, "abc", None, 1.5])
def test_request_rejects_invalid_caja_destino_id(value) -> None:
    with pytest.raises(ValidationError):
        EndosarChequeRequest(caja_destino_id=value)


def test_request_requires_caja_destino_id() -> None:
    with pytest.raises(ValidationError):
        EndosarChequeRequest()


def test_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        EndosarChequeRequest(caja_destino_id=4, descripcion="libre")
    with pytest.raises(ValidationError):
        EndosarChequeRequest(caja_destino_id=4, monto="1.00")


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


def _mov(**kwargs) -> Movimiento:
    base = dict(
        id=77,
        caja_id=3,
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
    mov = Movimiento(**base)
    mov.caja = CAJA_A
    return mov


def _user(rol: str) -> MagicMock:
    user = MagicMock()
    user.rol = rol
    return user


def test_pending_cheque_is_endosable_for_secretaria_only() -> None:
    cheque = _mov(instrumento="cheque", subtotal=None, fecha_liquidacion=date(2030, 1, 1))

    assert movimiento_to_response(cheque, _user("secretaria")).endosable is True
    assert movimiento_to_response(cheque, _user("escribano")).endosable is False


def test_common_and_liquidated_movements_are_not_endosable() -> None:
    comun = _mov()
    liquidado = _mov(
        instrumento="cheque",
        fecha_liquidacion=date(2030, 1, 1),
        fecha_liquidado=T_LIQUIDADO,
    )
    assert movimiento_to_response(comun, _user("secretaria")).endosable is False
    assert movimiento_to_response(liquidado, _user("secretaria")).endosable is False


def test_endorsed_cheque_exposes_destination_and_is_not_editable() -> None:
    cheque = _mov(
        instrumento="cheque",
        fecha_liquidacion=date(2030, 1, 1),
        fecha_liquidado=T_LIQUIDADO,
        subtotal=Decimal("10.00"),
        endosado_a_caja_id=4,
    )
    cheque.endosado_a_caja = CAJA_B

    resp = movimiento_to_response(cheque, _user("secretaria"))

    assert resp.estado == "liquidado"
    assert resp.endosado_a is not None
    assert resp.endosado_a.id == 4
    assert resp.endosado_a.nombre == "Martin"
    assert resp.endose_origen is None
    assert resp.endosable is False
    assert resp.liquidable is False
    assert resp.editable is False


def test_endose_movement_exposes_origin_and_is_not_editable() -> None:
    origen = _mov(
        id=50,
        instrumento="cheque",
        fecha_liquidacion=date(2030, 1, 1),
        fecha_liquidado=T_LIQUIDADO,
        endosado_a_caja_id=4,
    )
    origen.caja = CAJA_A
    destino = _mov(id=51, caja_id=4, tipo="salida", endose_cheque_id=50)
    destino.caja = CAJA_B
    destino.endose_cheque = origen

    resp = movimiento_to_response(destino, _user("secretaria"))

    assert resp.endose_origen is not None
    assert resp.endose_origen.cheque_id == 50
    assert resp.endose_origen.caja.id == 3
    assert resp.endose_origen.caja.nombre == "Ebel"
    assert resp.endosado_a is None
    assert resp.editable is False


def test_regular_movements_keep_editable_for_secretaria_and_default_endose_fields() -> None:
    resp = movimiento_to_response(_mov(), _user("secretaria"))
    assert resp.editable is True
    assert resp.endosado_a is None
    assert resp.endose_origen is None
    assert resp.endosable is False
