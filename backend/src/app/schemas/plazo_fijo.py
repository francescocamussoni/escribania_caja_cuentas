import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.dates import today_ar
from app.models.plazo_fijo import PlazoFijo
from app.schemas.caja import CajaResponse

MONTO_PATTERN = re.compile(r"^\d+(\.\d{1,2})?$")


def _validate_monto_string(value: str) -> str:
    if not MONTO_PATTERN.match(value):
        raise ValueError("monto inválido")
    if Decimal(value) <= 0:
        raise ValueError("monto debe ser mayor que cero")
    return value


def _validate_montos_order(monto_ingresado: str, monto_a_vencimiento: str) -> None:
    if Decimal(monto_a_vencimiento) < Decimal(monto_ingresado):
        raise ValueError("monto_a_vencimiento debe ser mayor o igual a monto_ingresado")


class CreatePlazoFijoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monto_ingresado: str
    monto_a_vencimiento: str
    fecha_vencimiento: date

    @field_validator("monto_ingresado", "monto_a_vencimiento")
    @classmethod
    def validate_monto(cls, value: str) -> str:
        return _validate_monto_string(value)

    @model_validator(mode="after")
    def validate_montos_relation(self) -> "CreatePlazoFijoRequest":
        _validate_montos_order(self.monto_ingresado, self.monto_a_vencimiento)
        return self


class UpdatePlazoFijoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monto_ingresado: str | None = None
    monto_a_vencimiento: str | None = None
    fecha_vencimiento: date | None = None

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UpdatePlazoFijoRequest":
        if (
            self.monto_ingresado is None
            and self.monto_a_vencimiento is None
            and self.fecha_vencimiento is None
        ):
            raise ValueError("debe enviar al menos un campo para actualizar")
        return self

    @field_validator("monto_ingresado", "monto_a_vencimiento")
    @classmethod
    def validate_monto(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_monto_string(value)

    @model_validator(mode="after")
    def validate_montos_relation(self) -> "UpdatePlazoFijoRequest":
        if self.monto_ingresado is not None and self.monto_a_vencimiento is not None:
            _validate_montos_order(self.monto_ingresado, self.monto_a_vencimiento)
        return self


class PlazoFijoResponse(BaseModel):
    id: int
    monto_ingresado: str
    monto_a_vencimiento: str
    fecha_vencimiento: date
    vencido: bool
    created_at: datetime
    caja: CajaResponse


class PlazosFijosResumenResponse(BaseModel):
    caja: CajaResponse
    total_monto_ingresado_activos: str
    total_monto_a_vencimiento_activos: str


class PaginatedPlazosFijosResponse(BaseModel):
    items: list[PlazoFijoResponse]
    page: int
    page_size: int
    total_items: int
    total_pages: int


def format_decimal(value: Decimal) -> str:
    return f"{value:.2f}"


def is_vencido(fecha_vencimiento: date, reference_today: date | None = None) -> bool:
    today = reference_today if reference_today is not None else today_ar()
    return fecha_vencimiento < today


def plazo_fijo_to_response(
    plazo_fijo: PlazoFijo,
    reference_today: date | None = None,
) -> PlazoFijoResponse:
    return PlazoFijoResponse(
        id=plazo_fijo.id,
        monto_ingresado=format_decimal(plazo_fijo.monto_ingresado),
        monto_a_vencimiento=format_decimal(plazo_fijo.monto_a_vencimiento),
        fecha_vencimiento=plazo_fijo.fecha_vencimiento,
        vencido=is_vencido(plazo_fijo.fecha_vencimiento, reference_today),
        created_at=plazo_fijo.created_at,
        caja=CajaResponse.model_validate(plazo_fijo.caja),
    )
