import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.schemas.caja import CajaResponse

MONTO_PATTERN = re.compile(r"^\d+(\.\d{1,2})?$")

# Shared literal for all schemas; only ARS and USD are valid currencies.
Moneda = Literal["ARS", "USD"]


class CreateMovimientoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descripcion: str = Field(min_length=1, max_length=500)
    monto: str
    tipo: str
    moneda: Moneda = "ARS"
    registrar_complementario: bool = False

    @field_validator("descripcion")
    @classmethod
    def validate_descripcion(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("descripcion no puede estar vacía")
        return cleaned

    @field_validator("monto")
    @classmethod
    def validate_monto(cls, value: str) -> str:
        if not MONTO_PATTERN.match(value):
            raise ValueError("monto inválido")
        return value

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, value: str) -> str:
        if value not in {"entrada", "salida"}:
            raise ValueError("tipo debe ser 'entrada' o 'salida'")
        return value

    @model_validator(mode="after")
    def validate_complementario_only_for_usd(self) -> "CreateMovimientoRequest":
        if self.registrar_complementario and self.moneda != "USD":
            raise ValueError(
                "registrar_complementario solo está permitido cuando moneda='USD'"
            )
        return self


class UpdateMovimientoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descripcion: str | None = Field(default=None, min_length=1, max_length=500)
    monto: str | None = None
    tipo: str | None = None
    moneda: Moneda | None = None

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UpdateMovimientoRequest":
        if (
            self.descripcion is None
            and self.monto is None
            and self.tipo is None
            and self.moneda is None
        ):
            raise ValueError("debe enviar al menos un campo para actualizar")
        return self

    @field_validator("descripcion")
    @classmethod
    def validate_descripcion(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("descripcion no puede estar vacía")
        return cleaned

    @field_validator("monto")
    @classmethod
    def validate_monto(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not MONTO_PATTERN.match(value):
            raise ValueError("monto inválido")
        return value

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in {"entrada", "salida"}:
            raise ValueError("tipo debe ser 'entrada' o 'salida'")
        return value


class MovimientoResponse(BaseModel):
    id: int
    descripcion: str
    monto: str
    tipo: str
    moneda: Moneda
    subtotal: str
    fecha: datetime
    editable: bool
    caja: CajaResponse


class MovimientoCreateResponse(BaseModel):
    """Response for POST /movimientos. Always includes movimiento; complementario is null for now (US2 adds it)."""

    movimiento: MovimientoResponse
    complementario: MovimientoResponse | None = None


class PaginatedMovimientosResponse(BaseModel):
    items: list[MovimientoResponse]
    page: int
    page_size: int
    total_items: int
    total_pages: int


def format_decimal(value: Decimal) -> str:
    return f"{value:.2f}"


def is_editable(_movimiento: Movimiento, user: Usuario) -> bool:
    return user.rol == "secretaria"


def movimiento_to_response(movimiento: Movimiento, user: Usuario) -> MovimientoResponse:
    return MovimientoResponse(
        id=movimiento.id,
        descripcion=movimiento.descripcion,
        monto=format_decimal(movimiento.monto),
        tipo=movimiento.tipo,
        moneda=movimiento.moneda,
        subtotal=format_decimal(movimiento.subtotal),
        fecha=movimiento.created_at,
        editable=is_editable(movimiento, user),
        caja=CajaResponse.model_validate(movimiento.caja),
    )
