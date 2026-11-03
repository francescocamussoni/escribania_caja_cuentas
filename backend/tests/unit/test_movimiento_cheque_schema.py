"""
T018 — TDD: `CreateMovimientoRequest` y `MovimientoResponse` con cheques (feature 010, US1).

Reglas (spec FR-001–FR-007, research §6):
  - instrumento ∈ {ninguno (default), cheque, echeque}
  - cheque/echeque ⇒ fecha_liquidacion obligatoria, formato YYYY-MM-DD, calendario válido,
    ESTRICTAMENTE posterior a hoy (Argentina).
  - ninguno ⇒ fecha_liquidacion prohibida.
  - cheque/echeque + registrar_complementario=true ⇒ inválido.
  - extra="forbid".
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

import app.models  # noqa: F401
from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.schemas.movimiento import CreateMovimientoRequest, movimiento_to_response

HOY = date(2026, 10, 21)


@pytest.fixture(autouse=True)
def _fixed_today():
    with patch("app.schemas.movimiento.today_ar", return_value=HOY):
        yield


def _payload(**overrides) -> dict:
    base = {"descripcion": "Cheque cliente", "monto": "500.00", "tipo": "entrada"}
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Request: compatibilidad hacia atrás
# ---------------------------------------------------------------------------


def test_default_instrumento_is_ninguno() -> None:
    req = CreateMovimientoRequest(**_payload())
    assert req.instrumento == "ninguno"
    assert req.fecha_liquidacion is None


def test_ninguno_without_fecha_liquidacion_is_valid_and_complementario_still_works() -> None:
    req = CreateMovimientoRequest(**_payload(registrar_complementario=True))
    assert req.registrar_complementario is True


# ---------------------------------------------------------------------------
# Request: cheque / echeque
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("instrumento", ["cheque", "echeque"])
def test_cheque_with_future_fecha_liquidacion_is_valid(instrumento: str) -> None:
    req = CreateMovimientoRequest(
        **_payload(instrumento=instrumento, fecha_liquidacion="2026-10-22")
    )
    assert req.instrumento == instrumento
    assert req.fecha_liquidacion == "2026-10-22"


@pytest.mark.parametrize("instrumento", ["cheque", "echeque"])
def test_cheque_without_fecha_liquidacion_fails(instrumento: str) -> None:
    with pytest.raises(ValidationError):
        CreateMovimientoRequest(**_payload(instrumento=instrumento))


@pytest.mark.parametrize("fecha", ["2026-10-21", "2026-10-20", "2020-01-01"])
def test_fecha_liquidacion_today_or_past_fails(fecha: str) -> None:
    with pytest.raises(ValidationError):
        CreateMovimientoRequest(**_payload(instrumento="cheque", fecha_liquidacion=fecha))


@pytest.mark.parametrize("fecha", ["21/10/2026", "2026-1-5", "mañana", "", "2026-10-22T10:00"])
def test_fecha_liquidacion_invalid_format_fails(fecha: str) -> None:
    with pytest.raises(ValidationError):
        CreateMovimientoRequest(**_payload(instrumento="cheque", fecha_liquidacion=fecha))


def test_fecha_liquidacion_non_calendar_date_fails() -> None:
    with pytest.raises(ValidationError):
        CreateMovimientoRequest(**_payload(instrumento="cheque", fecha_liquidacion="2026-02-30"))


def test_ninguno_with_fecha_liquidacion_fails() -> None:
    with pytest.raises(ValidationError):
        CreateMovimientoRequest(**_payload(fecha_liquidacion="2026-10-22"))
    with pytest.raises(ValidationError):
        CreateMovimientoRequest(
            **_payload(instrumento="ninguno", fecha_liquidacion="2026-10-22")
        )


@pytest.mark.parametrize("instrumento", ["cheque", "echeque"])
def test_cheque_with_registrar_complementario_fails(instrumento: str) -> None:
    with pytest.raises(ValidationError):
        CreateMovimientoRequest(
            **_payload(
                instrumento=instrumento,
                fecha_liquidacion="2026-10-22",
                registrar_complementario=True,
            )
        )


def test_invalid_instrumento_value_fails() -> None:
    with pytest.raises(ValidationError):
        CreateMovimientoRequest(**_payload(instrumento="pagare", fecha_liquidacion="2026-10-22"))


def test_cheque_accepts_fecha_manual_as_fecha_de_carga() -> None:
    req = CreateMovimientoRequest(
        **_payload(instrumento="echeque", fecha_liquidacion="2026-11-01", fecha_manual="2026-10-15")
    )
    assert req.fecha_manual == "2026-10-15"


def test_extra_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError):
        CreateMovimientoRequest(**_payload(estado="liquidado"))


# ---------------------------------------------------------------------------
# Response DTO
# ---------------------------------------------------------------------------

T_CREATED = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)
T_OVERRIDE = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
T_LIQUIDADO = datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)


def _mov(**kwargs) -> Movimiento:
    caja = Caja(id=3, nombre="Ebel", slug="ebel", estado="activa")
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
    mov.caja = caja
    return mov


def _user(rol: str) -> MagicMock:
    user = MagicMock()
    user.rol = rol
    return user


def test_response_for_common_movement() -> None:
    resp = movimiento_to_response(_mov(), _user("secretaria"))
    assert resp.instrumento == "ninguno"
    assert resp.estado is None
    assert resp.subtotal == "10.00"
    assert resp.fecha_liquidacion is None
    assert resp.fecha_liquidado is None
    assert resp.liquidable is False
    assert resp.editable is True


def test_response_for_pending_cheque() -> None:
    mov = _mov(
        instrumento="cheque",
        subtotal=None,
        fecha_liquidacion=date(2026, 11, 5),
        fecha_override=T_OVERRIDE,
    )
    resp = movimiento_to_response(mov, _user("secretaria"))
    assert resp.instrumento == "cheque"
    assert resp.estado == "pendiente"
    assert resp.subtotal is None
    assert resp.fecha_liquidacion == date(2026, 11, 5)
    assert resp.fecha_liquidado is None
    # Pendiente: la fecha mostrada es la fecha de carga
    assert resp.fecha == resp.fecha_carga
    assert resp.fecha_carga == T_OVERRIDE
    assert resp.liquidable is True


def test_response_pending_cheque_is_not_liquidable_for_escribano() -> None:
    mov = _mov(instrumento="echeque", subtotal=None, fecha_liquidacion=date(2026, 11, 5))
    resp = movimiento_to_response(mov, _user("escribano"))
    assert resp.estado == "pendiente"
    assert resp.liquidable is False
    assert resp.editable is False


def test_response_for_liquidated_cheque_uses_fecha_liquidado_as_fecha() -> None:
    mov = _mov(
        instrumento="cheque",
        fecha_liquidacion=date(2026, 11, 5),
        fecha_override=T_OVERRIDE,
        fecha_liquidado=T_LIQUIDADO,
        subtotal=Decimal("510.00"),
    )
    resp = movimiento_to_response(mov, _user("secretaria"))
    assert resp.estado == "liquidado"
    assert resp.subtotal == "510.00"
    assert resp.fecha == T_LIQUIDADO
    assert resp.fecha_carga == T_OVERRIDE
    assert resp.fecha_liquidado == T_LIQUIDADO
    assert resp.liquidable is False
