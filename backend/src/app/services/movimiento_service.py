from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.movimiento import Movimiento
from app.models.usuario import Usuario

VALID_TIPOS = frozenset({"entrada", "salida"})


class MovimientoNotFoundError(Exception):
    """Raised when a movimiento does not exist for the given caja."""


def compute_subtotal(previous: Decimal, monto: Decimal, tipo: str) -> Decimal:
    if tipo not in VALID_TIPOS:
        raise ValueError("tipo inválido: debe ser 'entrada' o 'salida'")
    if tipo == "entrada":
        return previous + monto
    return previous - monto


class MovimientoService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_movimiento(
        self,
        *,
        caja_id: int,
        descripcion: str,
        monto: Decimal,
        tipo: str,
        moneda: str = "ARS",
        user: Usuario,
    ) -> Movimiento:
        cleaned_description = descripcion.strip()
        if not cleaned_description:
            raise ValueError("descripcion no puede estar vacía")

        # Lock and fetch the last row of the *same currency stream* only.
        last_movimiento = self.db.scalar(
            select(Movimiento)
            .where(Movimiento.caja_id == caja_id, Movimiento.moneda == moneda)
            .order_by(Movimiento.created_at.desc(), Movimiento.id.desc())
            .with_for_update()
        )
        previous = last_movimiento.subtotal if last_movimiento else Decimal("0")
        subtotal = compute_subtotal(previous=previous, monto=monto, tipo=tipo)

        movimiento = Movimiento(
            caja_id=caja_id,
            descripcion=cleaned_description,
            monto=monto,
            tipo=tipo,
            moneda=moneda,
            subtotal=subtotal,
            created_by=user.id,
        )
        self.db.add(movimiento)
        self.db.flush()
        self.db.refresh(movimiento)
        return movimiento

    def create_movimiento_pair(
        self,
        *,
        caja_id: int,
        descripcion: str,
        monto: Decimal,
        tipo: str,
        user: "Usuario",
    ) -> "tuple[Movimiento, Movimiento]":
        """
        Create an atomic pair of USD movimientos with opposite tipos.
        Both are flushed in the same transaction; the caller must commit.
        Returns (principal, complementario).
        """
        principal = self.create_movimiento(
            caja_id=caja_id,
            descripcion=descripcion,
            monto=monto,
            tipo=tipo,
            moneda="USD",
            user=user,
        )
        complementario_tipo = "salida" if tipo == "entrada" else "entrada"
        complementario = self.create_movimiento(
            caja_id=caja_id,
            descripcion=principal.descripcion,
            monto=monto,
            tipo=complementario_tipo,
            moneda="USD",
            user=user,
        )
        return principal, complementario

    def recalculate_subtotals(self, caja_id: int, moneda: str = "ARS") -> None:
        """Recalculate subtotals for a single currency stream (caja_id, moneda)."""
        movimientos = self.db.scalars(
            select(Movimiento)
            .where(Movimiento.caja_id == caja_id, Movimiento.moneda == moneda)
            .order_by(Movimiento.created_at.asc(), Movimiento.id.asc())
            .with_for_update()
        ).all()

        previous = Decimal("0")
        for movimiento in movimientos:
            movimiento.subtotal = compute_subtotal(
                previous=previous,
                monto=movimiento.monto,
                tipo=movimiento.tipo,
            )
            previous = movimiento.subtotal
        self.db.flush()

    def update_movimiento(
        self,
        *,
        caja_id: int,
        movimiento_id: int,
        user: Usuario,
        descripcion: str | None = None,
        monto: Decimal | None = None,
        tipo: str | None = None,
        moneda: str | None = None,
    ) -> Movimiento:
        movimiento = self.db.scalar(
            select(Movimiento)
            .where(
                Movimiento.id == movimiento_id,
                Movimiento.caja_id == caja_id,
            )
            .with_for_update()
        )
        if movimiento is None:
            raise MovimientoNotFoundError()

        if descripcion is not None:
            cleaned_description = descripcion.strip()
            if not cleaned_description:
                raise ValueError("descripcion no puede estar vacía")
            movimiento.descripcion = cleaned_description
        if monto is not None:
            movimiento.monto = monto
        if tipo is not None:
            if tipo not in VALID_TIPOS:
                raise ValueError("tipo inválido: debe ser 'entrada' o 'salida'")
            movimiento.tipo = tipo

        # Detect whether the currency stream is changing before mutating.
        old_moneda = movimiento.moneda
        if moneda is not None and moneda != old_moneda:
            movimiento.moneda = moneda

        movimiento.updated_at = datetime.now(timezone.utc)
        movimiento.updated_by = user.id

        # Always recalculate the current (new) stream.
        self.recalculate_subtotals(caja_id, moneda=movimiento.moneda)
        # If the currency changed, also repair the stream that lost a row.
        if moneda is not None and moneda != old_moneda:
            self.recalculate_subtotals(caja_id, moneda=old_moneda)

        self.db.flush()
        self.db.refresh(movimiento)
        return movimiento

    def delete_movimiento(
        self,
        *,
        caja_id: int,
        movimiento_id: int,
        user: Usuario,
    ) -> None:
        movimiento = self.db.scalar(
            select(Movimiento)
            .where(
                Movimiento.id == movimiento_id,
                Movimiento.caja_id == caja_id,
            )
            .with_for_update()
        )
        if movimiento is None:
            raise MovimientoNotFoundError()

        self.db.delete(movimiento)
        self.db.flush()
        self.recalculate_subtotals(caja_id, moneda=movimiento.moneda)
