from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.caja import Caja


class Movimiento(Base):
    __tablename__ = "movimiento"
    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_movimiento_monto_positive"),
        CheckConstraint(
            "tipo IN ('entrada', 'salida')",
            name="ck_movimiento_tipo",
        ),
        CheckConstraint(
            "moneda IN ('ARS', 'USD')",
            name="ck_movimiento_moneda",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    caja_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("caja.id"),
        nullable=False,
    )
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="ARS")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    fecha_override: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    caja: Mapped["Caja"] = relationship(back_populates="movimientos")
