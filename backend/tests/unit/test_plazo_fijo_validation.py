"""Unit tests for plazo fijo amount validation (T005 — TDD, implement schemas in T010)."""

import pytest
from pydantic import ValidationError

from app.schemas.plazo_fijo import CreatePlazoFijoRequest, UpdatePlazoFijoRequest


def test_create_valid_plazo_fijo_request() -> None:
    payload = CreatePlazoFijoRequest(
        monto_ingresado="100000.00",
        monto_a_vencimiento="105000.00",
        fecha_vencimiento="2026-12-31",
    )
    assert payload.monto_ingresado == "100000.00"
    assert payload.monto_a_vencimiento == "105000.00"


def test_create_rejects_monto_a_vencimiento_less_than_ingresado() -> None:
    with pytest.raises(ValidationError):
        CreatePlazoFijoRequest(
            monto_ingresado="100000.00",
            monto_a_vencimiento="90000.00",
            fecha_vencimiento="2026-12-31",
        )


def test_create_rejects_zero_monto_ingresado() -> None:
    with pytest.raises(ValidationError):
        CreatePlazoFijoRequest(
            monto_ingresado="0",
            monto_a_vencimiento="100.00",
            fecha_vencimiento="2026-12-31",
        )


def test_create_rejects_negative_monto() -> None:
    with pytest.raises(ValidationError):
        CreatePlazoFijoRequest(
            monto_ingresado="-100.00",
            monto_a_vencimiento="100.00",
            fecha_vencimiento="2026-12-31",
        )


def test_create_allows_monto_a_vencimiento_equal_to_ingresado() -> None:
    payload = CreatePlazoFijoRequest(
        monto_ingresado="5000.00",
        monto_a_vencimiento="5000.00",
        fecha_vencimiento="2026-12-31",
    )
    assert payload.monto_a_vencimiento == "5000.00"


def test_create_rejects_invalid_monto_format() -> None:
    with pytest.raises(ValidationError):
        CreatePlazoFijoRequest(
            monto_ingresado="100.999",
            monto_a_vencimiento="105.00",
            fecha_vencimiento="2026-12-31",
        )


def test_update_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError):
        UpdatePlazoFijoRequest()


def test_update_rejects_monto_a_vencimiento_less_than_ingresado_when_both_sent() -> None:
    with pytest.raises(ValidationError):
        UpdatePlazoFijoRequest(
            monto_ingresado="10000.00",
            monto_a_vencimiento="5000.00",
        )


def test_update_partial_monto_ingresado_valid() -> None:
    payload = UpdatePlazoFijoRequest(monto_ingresado="2000.00")
    assert payload.monto_ingresado == "2000.00"
