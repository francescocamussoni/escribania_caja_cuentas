"""
T003 — TDD: validación del campo `moneda` en el modelo Movimiento.

Estos tests deben FALLAR hasta que se implemente T004 (migración) y T005 (modelo).
Cubren:
  - Default de alta = 'ARS'
  - Solo se aceptan 'ARS' y 'USD'
  - Valores inválidos son rechazados (nivel Pydantic + schema)
  - El campo `moneda` está presente en CreateMovimientoRequest y UpdateMovimientoRequest
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Modelo ORM: el campo `moneda` debe existir en Movimiento
# ---------------------------------------------------------------------------

def test_movimiento_model_has_moneda_attribute() -> None:
    """El modelo ORM Movimiento debe tener el campo `moneda`."""
    from app.models.movimiento import Movimiento

    assert hasattr(Movimiento, "moneda"), (
        "Movimiento no tiene el atributo `moneda`. Implementar T005."
    )


def test_movimiento_model_moneda_column_name() -> None:
    """La columna mapeada debe llamarse 'moneda' en la tabla."""
    from app.models.movimiento import Movimiento
    from sqlalchemy.inspection import inspect

    mapper = inspect(Movimiento)
    column_names = {col.key for col in mapper.mapper.column_attrs}
    assert "moneda" in column_names, (
        f"Columna 'moneda' no encontrada. Columnas disponibles: {column_names}"
    )


def test_movimiento_model_moneda_has_check_constraint() -> None:
    """La tabla debe definir un CHECK constraint para moneda IN ('ARS','USD')."""
    from app.models.movimiento import Movimiento
    from sqlalchemy.inspection import inspect

    table = inspect(Movimiento).persist_selectable
    check_names = [c.name for c in table.constraints if hasattr(c, "sqltext")]
    check_texts = [str(c.sqltext) for c in table.constraints if hasattr(c, "sqltext")]
    # Buscamos un constraint que mencione 'ARS' y 'USD'
    moneda_check = any("ARS" in t and "USD" in t for t in check_texts)
    assert moneda_check, (
        f"No se encontró CHECK constraint para moneda. "
        f"Constraints: {list(zip(check_names, check_texts))}"
    )


# ---------------------------------------------------------------------------
# Schema Pydantic: CreateMovimientoRequest
# ---------------------------------------------------------------------------

def test_create_request_default_moneda_is_ars() -> None:
    """Si no se envía `moneda`, el default debe ser 'ARS'."""
    from app.schemas.movimiento import CreateMovimientoRequest

    req = CreateMovimientoRequest(descripcion="Test", monto="100.00", tipo="entrada")
    assert req.moneda == "ARS", (
        f"Default de moneda esperado 'ARS', obtenido: {req.moneda!r}"
    )


def test_create_request_accepts_ars() -> None:
    """Debe aceptar moneda='ARS'."""
    from app.schemas.movimiento import CreateMovimientoRequest

    req = CreateMovimientoRequest(
        descripcion="Test", monto="100.00", tipo="entrada", moneda="ARS"
    )
    assert req.moneda == "ARS"


def test_create_request_accepts_usd() -> None:
    """Debe aceptar moneda='USD'."""
    from app.schemas.movimiento import CreateMovimientoRequest

    req = CreateMovimientoRequest(
        descripcion="Test", monto="100.00", tipo="entrada", moneda="USD"
    )
    assert req.moneda == "USD"


@pytest.mark.parametrize("invalid", ["EUR", "ars", "usd", "", "PESOS", "ARS ", " USD"])
def test_create_request_rejects_invalid_moneda(invalid: str) -> None:
    """Debe rechazar valores de moneda fuera del catálogo ARS/USD."""
    from app.schemas.movimiento import CreateMovimientoRequest

    with pytest.raises(ValidationError, match="moneda"):
        CreateMovimientoRequest(
            descripcion="Test", monto="100.00", tipo="entrada", moneda=invalid
        )


def test_create_request_rejects_extra_fields() -> None:
    """extra='forbid' debe seguir activo con el campo moneda."""
    from app.schemas.movimiento import CreateMovimientoRequest

    with pytest.raises(ValidationError):
        CreateMovimientoRequest(
            descripcion="Test",
            monto="100.00",
            tipo="entrada",
            moneda="ARS",
            campo_extra="x",
        )


def test_create_request_has_registrar_complementario_field() -> None:
    """El campo `registrar_complementario` debe existir y default False."""
    from app.schemas.movimiento import CreateMovimientoRequest

    req = CreateMovimientoRequest(
        descripcion="Test", monto="100.00", tipo="entrada", moneda="USD"
    )
    assert hasattr(req, "registrar_complementario"), (
        "CreateMovimientoRequest no tiene `registrar_complementario`. Implementar T006."
    )
    assert req.registrar_complementario is False


def test_create_request_complementario_true_rejected_for_ars() -> None:
    """registrar_complementario=True con moneda=ARS debe ser rechazado."""
    from app.schemas.movimiento import CreateMovimientoRequest

    with pytest.raises(ValidationError, match="complementario|ARS|moneda"):
        CreateMovimientoRequest(
            descripcion="Test",
            monto="100.00",
            tipo="entrada",
            moneda="ARS",
            registrar_complementario=True,
        )


# ---------------------------------------------------------------------------
# Schema Pydantic: UpdateMovimientoRequest
# ---------------------------------------------------------------------------

def test_update_request_accepts_moneda_ars() -> None:
    """PATCH puede incluir moneda='ARS'."""
    from app.schemas.movimiento import UpdateMovimientoRequest

    req = UpdateMovimientoRequest(moneda="ARS")
    assert req.moneda == "ARS"


def test_update_request_accepts_moneda_usd() -> None:
    """PATCH puede incluir moneda='USD'."""
    from app.schemas.movimiento import UpdateMovimientoRequest

    req = UpdateMovimientoRequest(moneda="USD")
    assert req.moneda == "USD"


@pytest.mark.parametrize("invalid", ["EUR", "ars", "pesos"])
def test_update_request_rejects_invalid_moneda(invalid: str) -> None:
    """PATCH debe rechazar moneda fuera del catálogo."""
    from app.schemas.movimiento import UpdateMovimientoRequest

    with pytest.raises(ValidationError, match="moneda"):
        UpdateMovimientoRequest(moneda=invalid)


def test_update_request_moneda_is_optional() -> None:
    """PATCH sin campo `moneda` sigue siendo válido."""
    from app.schemas.movimiento import UpdateMovimientoRequest

    req = UpdateMovimientoRequest(descripcion="Nueva descripción")
    assert req.moneda is None


# ---------------------------------------------------------------------------
# Schema Pydantic: MovimientoResponse
# ---------------------------------------------------------------------------

def test_movimiento_response_has_moneda_field() -> None:
    """MovimientoResponse debe exponer el campo `moneda`."""
    from app.schemas.movimiento import MovimientoResponse
    import inspect

    fields = MovimientoResponse.model_fields
    assert "moneda" in fields, (
        f"MovimientoResponse no tiene campo `moneda`. Campos: {list(fields.keys())}"
    )
