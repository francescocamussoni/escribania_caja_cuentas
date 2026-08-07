import calendar
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.core.dates import today_ar
from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.models.plazo_fijo import PlazoFijo
from app.schemas.informe import InformeModo, InformePdfRequest
from app.services.plazo_fijo_service import PlazosFijosResumen, _list_order_clauses

AR_TZ = "America/Argentina/Buenos_Aires"


class InformeDateRangeError(ValueError):
    """Raised when the resolved informe date range is invalid."""


def resolve_date_range(
    request: InformePdfRequest,
    *,
    reference_today: date | None = None,
) -> tuple[date, date]:
    today = reference_today if reference_today is not None else today_ar()

    if request.modo == InformeModo.MES_ANIO:
        if request.mes is None or request.anio is None:
            raise ValueError("mes y anio son obligatorios para modo MES_ANIO")
        date_from = date(request.anio, request.mes, 1)
        if request.hasta_hoy:
            date_to = today
        else:
            last_day = calendar.monthrange(request.anio, request.mes)[1]
            date_to = date(request.anio, request.mes, last_day)
    else:
        if request.fecha_inicio is None:
            raise ValueError("fecha_inicio es obligatoria para modo PERIODO")
        date_from = request.fecha_inicio
        if request.hasta_hoy:
            date_to = today
        else:
            if request.fecha_fin is None:
                raise ValueError("fecha_fin es obligatoria cuando hasta_hoy es false")
            date_to = request.fecha_fin

    if date_from > date_to:
        raise InformeDateRangeError("El rango de fechas es inválido")

    return date_from, date_to


def compute_saldo_cierre(movimientos: list[Movimiento]) -> Decimal | None:
    if not movimientos:
        return None
    latest = max(movimientos, key=lambda movimiento: (movimiento.created_at, movimiento.id))
    return latest.subtotal


def _movimiento_ar_date():
    return cast(func.timezone(AR_TZ, Movimiento.created_at), Date)


def _plazo_ar_date():
    return cast(func.timezone(AR_TZ, PlazoFijo.created_at), Date)


def compute_resumen_plazos_filtrado(
    plazos: list[PlazoFijo],
    *,
    reference_today: date | None = None,
) -> PlazosFijosResumen:
    today = reference_today if reference_today is not None else today_ar()
    total_ingresado = Decimal("0")
    total_vencimiento = Decimal("0")
    for plazo in plazos:
        if plazo.fecha_vencimiento >= today:
            total_ingresado += plazo.monto_ingresado
            total_vencimiento += plazo.monto_a_vencimiento
    return PlazosFijosResumen(
        total_monto_ingresado_activos=total_ingresado,
        total_monto_a_vencimiento_activos=total_vencimiento,
    )


class InformeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_caja(self, caja_id: int) -> Caja | None:
        return self.db.get(Caja, caja_id)

    def resolve_date_range(
        self,
        request: InformePdfRequest,
        *,
        reference_today: date | None = None,
    ) -> tuple[date, date]:
        return resolve_date_range(request, reference_today=reference_today)

    def fetch_movimientos_informe(
        self,
        *,
        caja_id: int,
        date_from: date,
        date_to: date,
    ) -> list[Movimiento]:
        movimiento_date = _movimiento_ar_date()
        return list(
            self.db.scalars(
                select(Movimiento)
                .where(
                    Movimiento.caja_id == caja_id,
                    movimiento_date >= date_from,
                    movimiento_date <= date_to,
                )
                .order_by(Movimiento.created_at.desc(), Movimiento.id.desc())
            ).all()
        )

    def fetch_saldo_actual(self, caja_id: int) -> Decimal:
        last_movimiento = self.db.scalar(
            select(Movimiento)
            .where(Movimiento.caja_id == caja_id)
            .order_by(Movimiento.created_at.desc(), Movimiento.id.desc())
        )
        return last_movimiento.subtotal if last_movimiento else Decimal("0")

    @staticmethod
    def compute_saldo_cierre(movimientos: list[Movimiento]) -> Decimal | None:
        return compute_saldo_cierre(movimientos)

    def fetch_plazos_informe(
        self,
        *,
        caja_id: int,
        date_from: date,
        date_to: date,
        reference_today: date | None = None,
    ) -> list[PlazoFijo]:
        today = reference_today if reference_today is not None else today_ar()
        plazo_date = _plazo_ar_date()
        return list(
            self.db.scalars(
                select(PlazoFijo)
                .where(
                    PlazoFijo.caja_id == caja_id,
                    plazo_date >= date_from,
                    plazo_date <= date_to,
                )
                .order_by(*_list_order_clauses(today))
            ).all()
        )

    @staticmethod
    def compute_resumen_plazos_filtrado(
        plazos: list[PlazoFijo],
        *,
        reference_today: date | None = None,
    ) -> PlazosFijosResumen:
        return compute_resumen_plazos_filtrado(plazos, reference_today=reference_today)
