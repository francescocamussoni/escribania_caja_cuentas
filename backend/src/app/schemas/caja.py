from pydantic import BaseModel, ConfigDict


class CajaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    slug: str


class CajaSaldoResponse(BaseModel):
    caja: CajaResponse
    saldo_actual: str
    ultimo_movimiento_at: str | None = None
