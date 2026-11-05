from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evento_configuracion_caja import EventoConfiguracionCaja
    from app.models.movimiento import Movimiento
    from app.models.plazo_fijo import PlazoFijo
    from app.models.usuario import Usuario


class Caja(Base):
    __tablename__ = "caja"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('activa', 'archivada')",
            name="ck_caja_estado",
        ),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="activa",
        server_default="activa",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    archived_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.id"),
        nullable=True,
    )

    movimientos: Mapped[list["Movimiento"]] = relationship(
        back_populates="caja",
        foreign_keys="Movimiento.caja_id",
    )
    plazos_fijos: Mapped[list["PlazoFijo"]] = relationship(
        back_populates="caja",
    )
    eventos_configuracion: Mapped[list["EventoConfiguracionCaja"]] = relationship(
        back_populates="caja",
    )
    archived_by: Mapped["Usuario | None"] = relationship()
