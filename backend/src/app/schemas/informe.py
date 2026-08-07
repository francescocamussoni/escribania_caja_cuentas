from datetime import date
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InformeTipo(str, Enum):
    CAJA = "CAJA"
    PLAZO_FIJO = "PLAZO_FIJO"


class InformeModo(str, Enum):
    MES_ANIO = "MES_ANIO"
    PERIODO = "PERIODO"


class InformePdfRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: InformeTipo
    caja_id: int = Field(ge=1, le=15)
    modo: InformeModo
    hasta_hoy: bool = False
    mes: int | None = Field(default=None, ge=1, le=12)
    anio: int | None = Field(default=None, ge=2000, le=2100)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None

    @model_validator(mode="after")
    def validate_temporal_fields(self) -> Self:
        if self.modo == InformeModo.MES_ANIO:
            if self.mes is None or self.anio is None:
                raise ValueError("mes y anio son obligatorios para modo MES_ANIO")
            if self.fecha_inicio is not None or self.fecha_fin is not None:
                raise ValueError("fecha_inicio y fecha_fin no aplican en modo MES_ANIO")
            return self

        if self.fecha_inicio is None:
            raise ValueError("fecha_inicio es obligatoria para modo PERIODO")
        if not self.hasta_hoy and self.fecha_fin is None:
            raise ValueError("fecha_fin es obligatoria cuando hasta_hoy es false")
        if self.mes is not None or self.anio is not None:
            raise ValueError("mes y anio no aplican en modo PERIODO")
        if not self.hasta_hoy and self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin")
        return self
