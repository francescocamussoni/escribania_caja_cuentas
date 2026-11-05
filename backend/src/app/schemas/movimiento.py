import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.dates import today_ar
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.schemas.caja import CajaResponse

MONTO_PATTERN = re.compile(r"^\d+(\.\d{1,2})?$")
FECHA_MANUAL_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Shared literal for all schemas; only ARS and USD are valid currencies.
Moneda = Literal["ARS", "USD"]

# Instrumento of a movimiento ("-" in the UI is "ninguno"). Cheque/Echeque are settled later.
Instrumento = Literal["ninguno", "cheque", "echeque"]
EstadoCheque = Literal["pendiente", "liquidado"]


def _parse_calendar_date(value: str, field: str) -> date:
    """Strict YYYY-MM-DD → real calendar date (shared by fecha_manual / fecha_liquidacion)."""
    if not FECHA_MANUAL_PATTERN.match(value):
        raise ValueError(f"{field} debe tener formato YYYY-MM-DD (e.g. '2026-09-01')")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} no es una fecha válida: {value}") from exc


class CreateMovimientoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descripcion: str = Field(min_length=1, max_length=500)
    monto: str
    tipo: str
    moneda: Moneda = "ARS"
    registrar_complementario: bool = False
    fecha_manual: str | None = None  # T027: formato YYYY-MM-DD opcional (US3)
    # 010: "ninguno" keeps the previous behaviour; cheque/echeque are created PENDING.
    instrumento: Instrumento = "ninguno"
    fecha_liquidacion: str | None = None  # YYYY-MM-DD, required (and > today) for cheques

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

    @field_validator("fecha_manual")
    @classmethod
    def validate_fecha_manual(cls, value: str | None) -> str | None:
        """T027: Valida que fecha_manual tenga formato estricto YYYY-MM-DD."""
        if value is None:
            return value
        _parse_calendar_date(value, "fecha_manual")
        return value

    @field_validator("fecha_liquidacion")
    @classmethod
    def validate_fecha_liquidacion_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        _parse_calendar_date(value, "fecha_liquidacion")
        return value

    @model_validator(mode="after")
    def validate_instrumento_rules(self) -> "CreateMovimientoRequest":
        if self.instrumento == "ninguno":
            if self.fecha_liquidacion is not None:
                raise ValueError(
                    "fecha_liquidacion solo corresponde a un cheque o echeque"
                )
            return self

        if self.fecha_liquidacion is None:
            raise ValueError("fecha_liquidacion es obligatoria para cheque o echeque")
        if _parse_calendar_date(self.fecha_liquidacion, "fecha_liquidacion") <= today_ar():
            raise ValueError("fecha_liquidacion debe ser posterior a hoy")
        if self.registrar_complementario:
            raise ValueError("un cheque o echeque no admite 'Entrada y Salida'")
        return self


class UpdateMovimientoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descripcion: str | None = Field(default=None, min_length=1, max_length=500)
    monto: str | None = None
    tipo: str | None = None
    moneda: Moneda | None = None
    # 010: a cheque can only switch between cheque and echeque ("ninguno" is not accepted:
    # a movement never becomes a common one again, nor a common one a cheque).
    instrumento: Literal["cheque", "echeque"] | None = None
    # Only editable on pending cheques; same rules as on creation (> today).
    fecha_liquidacion: str | None = None

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UpdateMovimientoRequest":
        if (
            self.descripcion is None
            and self.monto is None
            and self.tipo is None
            and self.moneda is None
            and self.instrumento is None
            and self.fecha_liquidacion is None
        ):
            raise ValueError("debe enviar al menos un campo para actualizar")
        return self

    @field_validator("fecha_liquidacion")
    @classmethod
    def validate_fecha_liquidacion(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if _parse_calendar_date(value, "fecha_liquidacion") <= today_ar():
            raise ValueError("fecha_liquidacion debe ser posterior a hoy")
        return value

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


class EndosarChequeRequest(BaseModel):
    """Body of POST .../endosar. The client only picks the destination caja: amounts,
    tipo and the description of the generated movement are decided by the server."""

    model_config = ConfigDict(extra="forbid")

    caja_destino_id: int = Field(ge=1, le=32767, strict=True)


class EndoseOrigen(BaseModel):
    """On the movement generated by an endorsement: the caja and cheque it comes from."""

    caja: CajaResponse
    cheque_id: int


class MovimientoResponse(BaseModel):
    id: int
    descripcion: str
    monto: str
    tipo: str
    moneda: Moneda
    # None only for pending cheques (they do not impact the balance).
    subtotal: str | None
    # Effective date: fecha_liquidado > fecha manual > created_at (pending: fecha de carga).
    fecha: datetime
    editable: bool
    caja: CajaResponse
    instrumento: Instrumento = "ninguno"
    estado: EstadoCheque | None = None
    fecha_carga: datetime
    fecha_liquidacion: date | None = None
    fecha_liquidado: datetime | None = None
    # True when the cheque is pending and the user can settle it (secretaria).
    liquidable: bool = False
    # True when the cheque is pending and the user can endorse it (secretaria).
    endosable: bool = False
    # Feature 011: destination caja (only on an endorsed cheque).
    endosado_a: CajaResponse | None = None
    # Feature 011: origin caja/cheque (only on the movement generated by an endorsement).
    endose_origen: EndoseOrigen | None = None
    # Running "Valor de caja total" (settled + pending cheques). Secretaria's Registro list only.
    valor_total: str | None = None


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


def is_editable(movimiento: Movimiento, user: Usuario) -> bool:
    # Endorsed cheques and the movements they generate are final (feature 011, FR-019).
    return user.rol == "secretaria" and not movimiento.bloqueado_por_endose


def movimiento_to_response(movimiento: Movimiento, user: Usuario) -> MovimientoResponse:
    from zoneinfo import ZoneInfo

    _AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

    def _to_ar(value: datetime) -> datetime:
        # Serialized with the Argentina offset (-03:00) instead of UTC "Z".
        return value.astimezone(_AR_TZ)

    # fecha de carga: manual date when present, else the INSERT time.
    # (created_at keeps its stored offset, as before, when there is no manual date.)
    fecha_carga = (
        _to_ar(movimiento.fecha_override)
        if movimiento.fecha_override is not None
        else movimiento.created_at
    )
    # Effective date: a settled cheque is placed by its liquidation time.
    fecha = (
        _to_ar(movimiento.fecha_liquidado)
        if movimiento.fecha_liquidado is not None
        else fecha_carga
    )

    return MovimientoResponse(
        id=movimiento.id,
        descripcion=movimiento.descripcion,
        monto=format_decimal(movimiento.monto),
        tipo=movimiento.tipo,
        moneda=movimiento.moneda,
        subtotal=(
            format_decimal(movimiento.subtotal) if movimiento.subtotal is not None else None
        ),
        fecha=fecha,
        editable=is_editable(movimiento, user),
        caja=CajaResponse.model_validate(movimiento.caja),
        instrumento=movimiento.instrumento,
        estado=movimiento.estado_cheque,
        fecha_carga=fecha_carga,
        fecha_liquidacion=movimiento.fecha_liquidacion,
        fecha_liquidado=(
            _to_ar(movimiento.fecha_liquidado)
            if movimiento.fecha_liquidado is not None
            else None
        ),
        liquidable=movimiento.estado_cheque == "pendiente" and user.rol == "secretaria",
        endosable=movimiento.estado_cheque == "pendiente" and user.rol == "secretaria",
        endosado_a=(
            CajaResponse.model_validate(movimiento.endosado_a_caja)
            if movimiento.endosado_a_caja is not None
            else None
        ),
        endose_origen=(
            EndoseOrigen(
                caja=CajaResponse.model_validate(movimiento.endose_cheque.caja),
                cheque_id=movimiento.endose_cheque.id,
            )
            if movimiento.endose_cheque is not None
            else None
        ),
    )


class EndoseResponse(BaseModel):
    """Both records touched by an endorsement."""

    cheque: MovimientoResponse
    movimiento_destino: MovimientoResponse


class SaldoFuturoDetalle(BaseModel):
    """A pending cheque inside a saldo-a-futuro row (what was entered)."""

    descripcion: str
    instrumento: Literal["cheque", "echeque"]
    tipo: Literal["entrada", "salida"]
    monto: str


class SaldoFuturoFila(BaseModel):
    fecha_liquidacion: date
    vencido: bool
    cheques: int
    efecto_neto: str
    saldo_proyectado: str
    detalle: list[SaldoFuturoDetalle]


class SaldoFuturoMoneda(BaseModel):
    moneda: Moneda
    saldo_actual: str
    filas: list[SaldoFuturoFila]


class SaldoFuturoResponse(BaseModel):
    caja: CajaResponse
    fecha_calculo: date
    monedas: list[SaldoFuturoMoneda]


class SaldoProyectadoMoneda(BaseModel):
    """Valor de caja total on a chosen date, for one moneda."""

    moneda: Moneda
    saldo_actual: str
    efecto_cheques: str
    saldo_proyectado: str
    cheques: int


class SaldoProyectadoResponse(BaseModel):
    caja: CajaResponse
    # None = no date chosen: every pending cheque is included.
    fecha: date | None
    monedas: list[SaldoProyectadoMoneda]
