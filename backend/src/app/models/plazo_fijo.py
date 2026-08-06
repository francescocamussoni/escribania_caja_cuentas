from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.caja import Caja


class PlazoFijo(Base):
    __tablename__ = "plazo_fijo"
    __table_args__ = (
        CheckConstraint("monto_ingresado > 0", name="ck_plazo_fijo_monto_ingresado_positive"),
        CheckConstraint(
            "monto_a_vencimiento > 0",
            name="ck_plazo_fijo_monto_a_vencimiento_positive",
        ),
        CheckConstraint(
            "monto_a_vencimiento >= monto_ingresado",
            name="ck_plazo_fijo_montos_order",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    caja_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("caja.id"),
        nullable=False,
    )
    monto_ingresado: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    monto_a_vencimiento: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)

    caja: Mapped["Caja"] = relationship(back_populates="plazos_fijos")
