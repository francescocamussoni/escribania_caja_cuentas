"""Helpers compartidos por los tests de cheques (feature 010).

Insertan filas directamente en la DB (con commit) para preparar escenarios que la API
todavía no puede crear o que requieren fechas controladas.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario


def insert_cheque(
    caja_id: int,
    *,
    tipo: str = "entrada",
    monto: str = "100.00",
    moneda: str = "ARS",
    instrumento: str = "cheque",
    fecha_liquidacion: date = date(2030, 1, 15),
    fecha_liquidado: datetime | None = None,
    fecha_override: datetime | None = None,
    created_at: datetime | None = None,
    subtotal: str | None = None,
    descripcion: str = "cheque de prueba",
) -> int:
    """Inserta un cheque (pendiente por defecto) y devuelve su id."""
    with SessionLocal() as session:
        user = session.scalar(select(Usuario).where(Usuario.username == "admin"))
        assert user is not None
        mov = Movimiento(
            caja_id=caja_id,
            descripcion=descripcion,
            monto=Decimal(monto),
            tipo=tipo,
            moneda=moneda,
            instrumento=instrumento,
            fecha_liquidacion=fecha_liquidacion,
            fecha_liquidado=fecha_liquidado,
            fecha_override=fecha_override,
            subtotal=Decimal(subtotal) if subtotal is not None else None,
            created_by=user.id,
            **({"created_at": created_at} if created_at else {}),
        )
        session.add(mov)
        session.commit()
        return mov.id


def get_movimiento(movimiento_id: int) -> Movimiento:
    with SessionLocal() as session:
        mov = session.get(Movimiento, movimiento_id)
        assert mov is not None
        session.expunge(mov)
        return mov
