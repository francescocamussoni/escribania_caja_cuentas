"""Pure projection of a caja's future balance from its pending cheques (feature 010).

No database access: the same function feeds the API (`GET .../saldo-futuro`) and the PDF
report, so both always show identical figures (SC-009). It is called once per moneda, so
ARS and USD never mix.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ChequeProyectable:
    """Minimal view of a pending cheque needed for the projection."""

    tipo: str  # "entrada" | "salida"
    monto: Decimal
    fecha_liquidacion: date
    descripcion: str = ""
    instrumento: str = ""  # "cheque" | "echeque"


@dataclass(frozen=True)
class DetalleCheque:
    """One pending cheque inside a row, so the user can tell what each amount is."""

    descripcion: str
    instrumento: str
    tipo: str
    monto: Decimal


@dataclass(frozen=True)
class FilaSaldoFuturo:
    fecha_liquidacion: date
    vencido: bool
    cheques: int
    efecto_neto: Decimal
    saldo_proyectado: Decimal
    detalle: tuple[DetalleCheque, ...] = ()


def _signed(cheque: ChequeProyectable) -> Decimal:
    return cheque.monto if cheque.tipo == "entrada" else -cheque.monto


def proyectar_saldo_futuro(
    saldo_actual: Decimal,
    cheques: Iterable[ChequeProyectable],
    hoy: date,
) -> list[FilaSaldoFuturo]:
    """One row per distinct fecha de liquidación, ascending, with the cumulative balance.

    `saldo_proyectado` of a row = `saldo_actual` + the net effect of every cheque whose
    fecha de liquidación is on or before that row's date. `vencido` means the date is
    today or earlier (the cheque is ready to be settled).
    """
    neto_por_fecha: dict[date, Decimal] = {}
    cantidad_por_fecha: dict[date, int] = {}
    detalle_por_fecha: dict[date, list[DetalleCheque]] = {}
    for cheque in cheques:
        fecha = cheque.fecha_liquidacion
        neto_por_fecha[fecha] = neto_por_fecha.get(fecha, Decimal("0")) + _signed(cheque)
        cantidad_por_fecha[fecha] = cantidad_por_fecha.get(fecha, 0) + 1
        detalle_por_fecha.setdefault(fecha, []).append(
            DetalleCheque(
                descripcion=cheque.descripcion,
                instrumento=cheque.instrumento,
                tipo=cheque.tipo,
                monto=cheque.monto,
            )
        )

    filas: list[FilaSaldoFuturo] = []
    acumulado = saldo_actual
    for fecha in sorted(neto_por_fecha):
        acumulado = acumulado + neto_por_fecha[fecha]
        filas.append(
            FilaSaldoFuturo(
                fecha_liquidacion=fecha,
                vencido=fecha <= hoy,
                cheques=cantidad_por_fecha[fecha],
                efecto_neto=neto_por_fecha[fecha],
                saldo_proyectado=acumulado,
                detalle=tuple(detalle_por_fecha[fecha]),
            )
        )
    return filas


def saldo_a_fecha(
    saldo_actual: Decimal,
    filas: Iterable[FilaSaldoFuturo],
    fecha: date,
) -> tuple[Decimal, Decimal, int]:
    """Balance on `fecha`: today's balance plus every pending cheque due on or before it.

    Returns (efecto_cheques, saldo_proyectado, cantidad_de_cheques). Overdue pending
    cheques (due date in the past, not settled yet) are included: they will move the
    balance as soon as they are settled. Built on the rows of `proyectar_saldo_futuro`,
    so it always agrees with the "Saldo a futuro" table.
    """
    efecto = Decimal("0")
    cheques = 0
    for fila in filas:
        if fila.fecha_liquidacion <= fecha:
            efecto += fila.efecto_neto
            cheques += fila.cheques
    return efecto, saldo_actual + efecto, cheques
