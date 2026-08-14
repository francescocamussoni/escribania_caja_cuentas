from pydantic import BaseModel, ConfigDict, Field, field_validator


class CajaCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=120)

    @field_validator("nombre")
    @classmethod
    def strip_nombre(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("nombre no puede estar vacío")
        return cleaned


class CajaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    slug: str
    estado: str = "activa"


class CajaSaldoResponse(BaseModel):
    caja: CajaResponse
    saldo_actual: str
    ultimo_movimiento_at: str | None = None


class CajaSaldoResumenItem(BaseModel):
    caja: CajaResponse
    saldo_actual: str


class CajaSaldoGeneralResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subtotal_general: str
    cajas_incluidas: int
    cajas: list[CajaSaldoResumenItem]
