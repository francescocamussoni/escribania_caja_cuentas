"""
T065 — TDD: `UpdateMovimientoRequest` con cheques (feature 010, US5).

  - instrumento solo admite cheque|echeque ("ninguno" ⇒ 422: no se vuelve a "-").
  - fecha_liquidacion: mismas reglas que al crear (YYYY-MM-DD válido, > hoy).
  - al menos un campo; extra="forbid".
"""

from datetime import date
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.schemas.movimiento import UpdateMovimientoRequest

HOY = date(2026, 10, 21)


@pytest.fixture(autouse=True)
def _fixed_today():
    with patch("app.schemas.movimiento.today_ar", return_value=HOY):
        yield


@pytest.mark.parametrize("instrumento", ["cheque", "echeque"])
def test_instrumento_cheque_or_echeque_is_valid_alone(instrumento: str) -> None:
    req = UpdateMovimientoRequest(instrumento=instrumento)
    assert req.instrumento == instrumento


@pytest.mark.parametrize("value", ["ninguno", "", "efectivo", "CHEQUE"])
def test_other_instrumento_values_fail(value: str) -> None:
    with pytest.raises(ValidationError):
        UpdateMovimientoRequest(instrumento=value)


def test_fecha_liquidacion_valid_alone() -> None:
    req = UpdateMovimientoRequest(fecha_liquidacion="2026-10-22")
    assert req.fecha_liquidacion == "2026-10-22"


@pytest.mark.parametrize("value", ["2026-10-21", "2026-10-20", "2020-01-01"])
def test_fecha_liquidacion_today_or_past_fails(value: str) -> None:
    with pytest.raises(ValidationError):
        UpdateMovimientoRequest(fecha_liquidacion=value)


@pytest.mark.parametrize("value", ["2026-13-01", "2026-02-30", "22/10/2026", "mañana", ""])
def test_fecha_liquidacion_bad_format_fails(value: str) -> None:
    with pytest.raises(ValidationError):
        UpdateMovimientoRequest(fecha_liquidacion=value)


def test_both_instrument_fields_together() -> None:
    req = UpdateMovimientoRequest(instrumento="echeque", fecha_liquidacion="2030-01-01")
    assert (req.instrumento, req.fecha_liquidacion) == ("echeque", "2030-01-01")


def test_instrument_fields_count_as_a_field_to_update() -> None:
    UpdateMovimientoRequest(fecha_liquidacion="2030-01-01")
    UpdateMovimientoRequest(instrumento="cheque")
    with pytest.raises(ValidationError):
        UpdateMovimientoRequest()


def test_extra_fields_are_still_forbidden() -> None:
    with pytest.raises(ValidationError):
        UpdateMovimientoRequest(instrumento="cheque", fecha_liquidado="2030-01-01")


def test_legacy_payloads_are_unchanged() -> None:
    req = UpdateMovimientoRequest(descripcion="x", monto="1.00", tipo="salida", moneda="USD")
    assert req.instrumento is None
    assert req.fecha_liquidacion is None
