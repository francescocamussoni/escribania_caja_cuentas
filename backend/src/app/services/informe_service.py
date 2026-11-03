import calendar
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.core.dates import today_ar
from app.models.caja import Caja
from app.models.movimiento import Movimiento, cheque_pendiente_expr, effective_date_expr
from app.models.plazo_fijo import PlazoFijo
from app.schemas.informe import InformeModo, InformePdfRequest
from app.services.cheque_service import build_saldo_futuro
from app.services.plazo_fijo_service import PlazosFijosResumen, _list_order_clauses
from app.services.saldo_futuro import FilaSaldoFuturo
from app.services.saldo_service import get_saldo_actual

AR_TZ = "America/Argentina/Buenos_Aires"

# Defensive cap for the "Cheques pendientes" section of the PDF.
MAX_CHEQUES_PENDIENTES_INFORME = 1000


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
    latest = max(movimientos, key=lambda movimiento: (movimiento.fecha_efectiva, movimiento.id))
    return latest.subtotal


def compute_saldo_cierre_by_moneda(
    movimientos: list[Movimiento],
    moneda: str,
) -> Decimal | None:
    """Return the closing subtotal for a specific currency stream."""
    filtered = [m for m in movimientos if m.moneda == moneda]
    if not filtered:
        return None
    latest = max(filtered, key=lambda m: (m.fecha_efectiva, m.id))
    return latest.subtotal


def _movimiento_ar_date():
    """Effective date (liquidation > manual > creation) as an Argentina calendar date."""
    return cast(func.timezone(AR_TZ, effective_date_expr()), Date)


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
        """Movements that impact the balance (pending cheques are excluded), by effective date."""
        movimiento_date = _movimiento_ar_date()
        return list(
            self.db.scalars(
                select(Movimiento)
                .where(
                    Movimiento.caja_id == caja_id,
                    Movimiento.subtotal.is_not(None),
                    movimiento_date >= date_from,
                    movimiento_date <= date_to,
                )
                .order_by(effective_date_expr().desc(), Movimiento.id.desc())
            ).all()
        )

    def fetch_saldo_ars(self, caja_id: int) -> Decimal:
        return get_saldo_actual(self.db, caja_id, "ARS")

    def fetch_saldo_usd(self, caja_id: int) -> Decimal:
        return get_saldo_actual(self.db, caja_id, "USD")

    def fetch_cheques_pendientes(self, caja_id: int) -> tuple[list[Movimiento], int]:
        """Pending cheques of the caja (current state, not filtered by period).

        Returns (items, total): items are capped at `MAX_CHEQUES_PENDIENTES_INFORME`.
        """
        condition = cheque_pendiente_expr() & (Movimiento.caja_id == caja_id)
        total = self.db.scalar(select(func.count()).select_from(Movimiento).where(condition)) or 0
        items = self.db.scalars(
            select(Movimiento)
            .where(condition)
            .order_by(Movimiento.fecha_liquidacion.asc(), Movimiento.id.asc())
            .limit(MAX_CHEQUES_PENDIENTES_INFORME)
        ).all()
        return list(items), total

    def fetch_saldo_futuro(
        self,
        caja_id: int,
        *,
        hoy: date | None = None,
    ) -> dict[str, tuple[Decimal, list[FilaSaldoFuturo]]]:
        """Same projection as `GET /cajas/{id}/saldo-futuro` (shared function)."""
        return build_saldo_futuro(self.db, caja_id, hoy if hoy is not None else today_ar())

    @staticmethod
    def compute_saldo_cierre(movimientos: list[Movimiento]) -> Decimal | None:
        return compute_saldo_cierre(movimientos)

    @staticmethod
    def compute_saldo_cierre_by_moneda(
        movimientos: list[Movimiento],
        moneda: str,
    ) -> Decimal | None:
        return compute_saldo_cierre_by_moneda(movimientos, moneda)

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
