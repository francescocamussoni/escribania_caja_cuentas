from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.dates import today_ar
from app.models.caja import Caja
from app.models.plazo_fijo import PlazoFijo
from app.models.usuario import Usuario

PAGE_SIZE = 20


class PlazoFijoNotFoundError(Exception):
    """Raised when a plazo fijo does not exist for the given caja."""


def plazo_fijo_list_sort_key(
    fecha_vencimiento: date,
    created_at: datetime,
    plazo_id: int,
    reference_today: date,
) -> tuple[int, int, float, int]:
    """Sort key: activos first (vencimiento asc), vencidos last (vencimiento desc)."""
    is_vencido = fecha_vencimiento < reference_today
    group = 1 if is_vencido else 0
    if is_vencido:
        venc_component = -fecha_vencimiento.toordinal()
    else:
        venc_component = fecha_vencimiento.toordinal()
    return (
        group,
        venc_component,
        -created_at.timestamp(),
        -plazo_id,
    )


def _validate_montos_order(monto_ingresado: Decimal, monto_a_vencimiento: Decimal) -> None:
    if monto_a_vencimiento < monto_ingresado:
        raise ValueError("monto_a_vencimiento debe ser mayor o igual a monto_ingresado")


def _list_order_clauses(reference_today: date) -> tuple:
    active_vencimiento = case(
        (PlazoFijo.fecha_vencimiento >= reference_today, PlazoFijo.fecha_vencimiento),
        else_=None,
    )
    vencido_vencimiento = case(
        (PlazoFijo.fecha_vencimiento < reference_today, PlazoFijo.fecha_vencimiento),
        else_=None,
    )
    return (
        (PlazoFijo.fecha_vencimiento < reference_today).asc(),
        active_vencimiento.asc().nulls_last(),
        vencido_vencimiento.desc().nulls_last(),
        PlazoFijo.created_at.desc(),
        PlazoFijo.id.desc(),
    )


class PlazosFijosResumen:
    def __init__(
        self,
        total_monto_ingresado_activos: Decimal,
        total_monto_a_vencimiento_activos: Decimal,
    ) -> None:
        self.total_monto_ingresado_activos = total_monto_ingresado_activos
        self.total_monto_a_vencimiento_activos = total_monto_a_vencimiento_activos


class PlazoFijoService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_plazo_fijo(
        self,
        *,
        caja_id: int,
        monto_ingresado: Decimal,
        monto_a_vencimiento: Decimal,
        fecha_vencimiento: date,
        user: Usuario,
    ) -> PlazoFijo:
        _validate_montos_order(monto_ingresado, monto_a_vencimiento)

        plazo_fijo = PlazoFijo(
            caja_id=caja_id,
            monto_ingresado=monto_ingresado,
            monto_a_vencimiento=monto_a_vencimiento,
            fecha_vencimiento=fecha_vencimiento,
            created_by=user.id,
        )
        self.db.add(plazo_fijo)
        self.db.flush()
        self.db.refresh(plazo_fijo)
        return plazo_fijo

    def update_plazo_fijo(
        self,
        *,
        caja_id: int,
        plazo_fijo_id: int,
        monto_ingresado: Decimal | None = None,
        monto_a_vencimiento: Decimal | None = None,
        fecha_vencimiento: date | None = None,
    ) -> PlazoFijo:
        plazo_fijo = self.db.scalar(
            select(PlazoFijo)
            .where(
                PlazoFijo.id == plazo_fijo_id,
                PlazoFijo.caja_id == caja_id,
            )
            .with_for_update()
        )
        if plazo_fijo is None:
            raise PlazoFijoNotFoundError()

        if monto_ingresado is not None:
            plazo_fijo.monto_ingresado = monto_ingresado
        if monto_a_vencimiento is not None:
            plazo_fijo.monto_a_vencimiento = monto_a_vencimiento
        if fecha_vencimiento is not None:
            plazo_fijo.fecha_vencimiento = fecha_vencimiento

        _validate_montos_order(
            plazo_fijo.monto_ingresado,
            plazo_fijo.monto_a_vencimiento,
        )

        self.db.flush()
        self.db.refresh(plazo_fijo)
        return plazo_fijo

    def delete_plazo_fijo(
        self,
        *,
        caja_id: int,
        plazo_fijo_id: int,
    ) -> None:
        plazo_fijo = self.db.scalar(
            select(PlazoFijo)
            .where(
                PlazoFijo.id == plazo_fijo_id,
                PlazoFijo.caja_id == caja_id,
            )
            .with_for_update()
        )
        if plazo_fijo is None:
            raise PlazoFijoNotFoundError()

        self.db.delete(plazo_fijo)
        self.db.flush()

    def list_plazos_fijos(
        self,
        *,
        caja_id: int,
        page: int,
        page_size: int = PAGE_SIZE,
    ) -> tuple[list[PlazoFijo], int]:
        reference_today = today_ar()

        total_items = self.db.scalar(
            select(func.count())
            .select_from(PlazoFijo)
            .where(PlazoFijo.caja_id == caja_id)
        )
        total_items = total_items or 0

        plazos_fijos = self.db.scalars(
            select(PlazoFijo)
            .where(PlazoFijo.caja_id == caja_id)
            .options(selectinload(PlazoFijo.caja))
            .order_by(*_list_order_clauses(reference_today))
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return plazos_fijos, total_items

    def get_resumen(self, *, caja_id: int) -> PlazosFijosResumen:
        reference_today = today_ar()

        totals = self.db.execute(
            select(
                func.coalesce(func.sum(PlazoFijo.monto_ingresado), 0),
                func.coalesce(func.sum(PlazoFijo.monto_a_vencimiento), 0),
            )
            .where(
                PlazoFijo.caja_id == caja_id,
                PlazoFijo.fecha_vencimiento >= reference_today,
            )
        ).one()

        return PlazosFijosResumen(
            total_monto_ingresado_activos=Decimal(str(totals[0])),
            total_monto_a_vencimiento_activos=Decimal(str(totals[1])),
        )

    def get_caja(self, caja_id: int) -> Caja | None:
        return self.db.get(Caja, caja_id)
