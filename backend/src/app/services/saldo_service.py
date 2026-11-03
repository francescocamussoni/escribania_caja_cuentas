"""Single source of truth for the current balance of a (caja, moneda) stream.

saldo = SUM(entrada +monto / salida -monto) over rows with `subtotal IS NOT NULL`
(common movements and settled cheques). Pending cheques never count.

Using a SUM instead of "the last row's subtotal" makes the balance independent of the
row order and of stored subtotals that may be stale (e.g. a back-dated movement).
"""

from collections.abc import Iterable
from decimal import Decimal

from datetime import timedelta

from sqlalchemy import DateTime, case, cast, func, select
from sqlalchemy.orm import Session

from app.models.movimiento import (
    Movimiento,
    cheque_pendiente_expr,
    effective_date_expr,
)

MONEDAS = ("ARS", "USD")
ZERO = Decimal("0.00")


def _signed_amount():
    return case(
        (Movimiento.tipo == "entrada", Movimiento.monto),
        else_=-Movimiento.monto,
    )


def get_saldo_actual(db: Session, caja_id: int, moneda: str) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(_signed_amount()), 0)).where(
            Movimiento.caja_id == caja_id,
            Movimiento.moneda == moneda,
            Movimiento.subtotal.is_not(None),
        )
    )
    return Decimal(total).quantize(ZERO)


def get_saldos_caja(db: Session, caja_id: int) -> tuple[Decimal, Decimal]:
    """Return (saldo_ars, saldo_usd) for one caja."""
    return get_saldos_cajas(db, [caja_id])[caja_id]


def get_saldos_cajas(
    db: Session,
    caja_ids: Iterable[int],
) -> dict[int, tuple[Decimal, Decimal]]:
    """Return {caja_id: (saldo_ars, saldo_usd)}; cajas without movements get zeros."""
    ids = list(caja_ids)
    result: dict[int, tuple[Decimal, Decimal]] = {cid: (ZERO, ZERO) for cid in ids}
    if not ids:
        return result

    rows = db.execute(
        select(
            Movimiento.caja_id,
            Movimiento.moneda,
            func.coalesce(func.sum(_signed_amount()), 0),
        )
        .where(Movimiento.caja_id.in_(ids), Movimiento.subtotal.is_not(None))
        .group_by(Movimiento.caja_id, Movimiento.moneda)
    ).all()

    acc: dict[int, dict[str, Decimal]] = {cid: {} for cid in ids}
    for caja_id, moneda, total in rows:
        acc[caja_id][moneda] = Decimal(total).quantize(ZERO)

    for cid in ids:
        result[cid] = (acc[cid].get("ARS", ZERO), acc[cid].get("USD", ZERO))
    return result


AR_TZ_NAME = "America/Argentina/Buenos_Aires"


def get_valores_totales(db: Session, caja_id: int, movimiento_ids: Iterable[int]) -> dict[int, Decimal]:
    """Running "Valor de caja total" after each given movement, per (caja, moneda).

    The stream holds settled rows plus pending cheques. Settled rows are ordered by their
    effective date; a pending cheque sits at the end of its fecha de liquidacion (overdue
    ones at "now"), so the last row of each moneda equals saldo actual + every pending
    cheque.
    """
    ids = list(movimiento_ids)
    if not ids:
        return {}

    fin_de_dia = func.timezone(
        AR_TZ_NAME,
        cast(Movimiento.fecha_liquidacion, DateTime) + timedelta(days=1),
    )
    orden = case(
        (cheque_pendiente_expr(), func.greatest(fin_de_dia, func.now())),
        else_=effective_date_expr(),
    )
    corrido = func.sum(_signed_amount()).over(
        partition_by=Movimiento.moneda,
        order_by=(orden, Movimiento.id),
    )
    subq = (
        select(Movimiento.id.label("id"), corrido.label("total"))
        .where(Movimiento.caja_id == caja_id)
        .subquery()
    )
    rows = db.execute(select(subq.c.id, subq.c.total).where(subq.c.id.in_(ids))).all()
    return {row_id: Decimal(total).quantize(ZERO) for row_id, total in rows}
