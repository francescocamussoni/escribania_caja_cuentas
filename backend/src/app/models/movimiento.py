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
    String,
    func,
    or_,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.caja import Caja


INSTRUMENTO_NINGUNO = "ninguno"
INSTRUMENTO_CHEQUE = "cheque"
INSTRUMENTO_ECHEQUE = "echeque"
INSTRUMENTOS_CHEQUE = frozenset({INSTRUMENTO_CHEQUE, INSTRUMENTO_ECHEQUE})

ESTADO_PENDIENTE = "pendiente"
ESTADO_LIQUIDADO = "liquidado"


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
        CheckConstraint(
            "instrumento IN ('ninguno', 'cheque', 'echeque')",
            name="ck_movimiento_instrumento",
        ),
        CheckConstraint(
            "(instrumento = 'ninguno' AND fecha_liquidacion IS NULL AND fecha_liquidado IS NULL) "
            "OR (instrumento <> 'ninguno' AND fecha_liquidacion IS NOT NULL)",
            name="ck_movimiento_cheque_fechas",
        ),
        CheckConstraint(
            "(subtotal IS NOT NULL) = (instrumento = 'ninguno' OR fecha_liquidado IS NOT NULL)",
            name="ck_movimiento_subtotal_estado",
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
    instrumento: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=INSTRUMENTO_NINGUNO,
    )
    # NULL only for pending cheques (they do not impact the balance).
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
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
    fecha_liquidacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_liquidado: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    caja: Mapped["Caja"] = relationship(back_populates="movimientos")

    # ------------------------------------------------------------------
    # Derived properties (not persisted) — see specs/010-cheques-instrumento/data-model.md
    # ------------------------------------------------------------------

    @property
    def es_cheque(self) -> bool:
        return self.instrumento != INSTRUMENTO_NINGUNO

    @property
    def estado_cheque(self) -> str | None:
        if not self.es_cheque:
            return None
        return ESTADO_PENDIENTE if self.fecha_liquidado is None else ESTADO_LIQUIDADO

    @property
    def impacta_saldo(self) -> bool:
        return self.subtotal is not None

    @property
    def fecha_carga(self) -> datetime:
        """Date the movement was loaded: the optional manual date, else the INSERT time."""
        return self.fecha_override or self.created_at

    @property
    def fecha_efectiva(self) -> datetime:
        """Date used to order / filter / balance: liquidation time wins for settled cheques."""
        return self.fecha_liquidado or self.fecha_override or self.created_at


def effective_date_expr():
    """SQL counterpart of `Movimiento.fecha_efectiva`."""
    return func.coalesce(
        Movimiento.fecha_liquidado,
        Movimiento.fecha_override,
        Movimiento.created_at,
    )


def impacta_saldo_expr():
    """SQL predicate: rows that take part in the (caja, moneda) stream.

    Defined by STATE (common movement or settled cheque) instead of `subtotal IS NOT NULL`
    so that a cheque being settled enters the stream before its subtotal is recomputed.
    """
    return or_(
        Movimiento.instrumento == INSTRUMENTO_NINGUNO,
        Movimiento.fecha_liquidado.is_not(None),
    )


def cheque_pendiente_expr():
    """SQL predicate: cheques/echeques not yet settled."""
    return (Movimiento.instrumento != INSTRUMENTO_NINGUNO) & Movimiento.fecha_liquidado.is_(None)
