from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.movimiento import Movimiento
    from app.models.plazo_fijo import PlazoFijo


class Caja(Base):
    __tablename__ = "caja"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    movimientos: Mapped[list["Movimiento"]] = relationship(
        back_populates="caja",
    )
    plazos_fijos: Mapped[list["PlazoFijo"]] = relationship(
        back_populates="caja",
    )
