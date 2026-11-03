"""Read queries over pending cheques/echeques (feature 010).

Pending cheques have no subtotal and never impact the balance; they are listed
separately from the chronological movimientos.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.movimiento import Movimiento, cheque_pendiente_expr
from app.services.saldo_futuro import (
    ChequeProyectable,
    FilaSaldoFuturo,
    proyectar_saldo_futuro,
)
from app.services.saldo_service import MONEDAS, get_saldos_caja

PAGE_SIZE = 20
AR_TZ_NAME = "America/Argentina/Buenos_Aires"


def fecha_carga_expr():
    """SQL counterpart of `Movimiento.fecha_carga`."""
    return func.coalesce(Movimiento.fecha_override, Movimiento.created_at)


def list_cheques_pendientes_page(
    db: Session,
    *,
    where: ColumnElement[bool],
    page: int,
) -> tuple[list[Movimiento], int]:
    """Return (items, total_items) for pending cheques matching `where`.

    Ordered by `fecha_liquidacion ASC, id ASC`; page size is fixed (20).
    """
    condition = cheque_pendiente_expr() & where
    total_items = (
        db.scalar(select(func.count()).select_from(Movimiento).where(condition)) or 0
    )
    items = db.scalars(
        select(Movimiento)
        .where(condition)
        .options(selectinload(Movimiento.caja))
        .order_by(Movimiento.fecha_liquidacion.asc(), Movimiento.id.asc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    return list(items), total_items


def build_saldo_futuro(
    db: Session,
    caja_id: int,
    hoy: date,
) -> dict[str, tuple[Decimal, list[FilaSaldoFuturo]]]:
    """Return {moneda: (saldo_actual, filas)} for one caja, ARS and USD independently.

    Shared by the API and the PDF report so both show the same numbers. Only lightweight
    columns of the pending cheques are read (no ORM entities).
    """
    saldos = dict(zip(MONEDAS, get_saldos_caja(db, caja_id), strict=True))
    rows = db.execute(
        select(
            Movimiento.moneda,
            Movimiento.tipo,
            Movimiento.monto,
            Movimiento.fecha_liquidacion,
            Movimiento.descripcion,
            Movimiento.instrumento,
        )
        .where(cheque_pendiente_expr(), Movimiento.caja_id == caja_id)
        .order_by(Movimiento.fecha_liquidacion.asc(), Movimiento.id.asc())
    ).all()

    por_moneda: dict[str, list[ChequeProyectable]] = {m: [] for m in MONEDAS}
    for moneda, tipo, monto, fecha_liquidacion, descripcion, instrumento in rows:
        por_moneda[moneda].append(
            ChequeProyectable(
                tipo=tipo,
                monto=monto,
                fecha_liquidacion=fecha_liquidacion,
                descripcion=descripcion,
                instrumento=instrumento,
            )
        )

    return {
        moneda: (saldos[moneda], proyectar_saldo_futuro(saldos[moneda], por_moneda[moneda], hoy))
        for moneda in MONEDAS
    }
