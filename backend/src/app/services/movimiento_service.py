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
        user: Usuario,
    ) -> Movimiento:
        cleaned_description = descripcion.strip()
        if not cleaned_description:
            raise ValueError("descripcion no puede estar vacía")

        last_movimiento = self.db.scalar(
            select(Movimiento)
            .where(Movimiento.caja_id == caja_id)
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
            subtotal=subtotal,
            created_by=user.id,
        )
        self.db.add(movimiento)
        self.db.flush()
        self.db.refresh(movimiento)
        return movimiento

    def recalculate_subtotals(self, caja_id: int) -> None:
        movimientos = self.db.scalars(
            select(Movimiento)
            .where(Movimiento.caja_id == caja_id)
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

        movimiento.updated_at = datetime.now(timezone.utc)
        movimiento.updated_by = user.id
        self.recalculate_subtotals(caja_id)
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
        self.recalculate_subtotals(caja_id)
