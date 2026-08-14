from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.caja import Caja
    from app.models.usuario import Usuario


class EventoConfiguracionCaja(Base):
    __tablename__ = "evento_configuracion_caja"
    __table_args__ = (
        CheckConstraint(
            "accion IN ('crear', 'archivar', 'desarchivar')",
            name="ck_evento_configuracion_caja_accion",
        ),
        CheckConstraint(
            "resultado IN ('exito', 'rechazo', 'error')",
            name="ck_evento_configuracion_caja_resultado",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caja_id: Mapped[int | None] = mapped_column(
        SmallInteger,
        ForeignKey("caja.id"),
        nullable=True,
    )
    accion: Mapped[str] = mapped_column(String(20), nullable=False)
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuario.id"),
        nullable=False,
    )
    detalle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    caja: Mapped["Caja | None"] = relationship(back_populates="eventos_configuracion")
    actor: Mapped["Usuario"] = relationship()
