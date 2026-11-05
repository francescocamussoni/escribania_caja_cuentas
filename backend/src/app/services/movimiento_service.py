from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.caja import Caja
from app.models.movimiento import (
    INSTRUMENTO_NINGUNO,
    INSTRUMENTOS_CHEQUE,
    Movimiento,
    effective_date_expr,
    impacta_saldo_expr,
)
from app.core.dates import today_ar
from app.models.usuario import Usuario

VALID_TIPOS = frozenset({"entrada", "salida"})
VALID_INSTRUMENTOS = frozenset({INSTRUMENTO_NINGUNO}) | INSTRUMENTOS_CHEQUE


class MovimientoNotFoundError(Exception):
    """Raised when a movimiento does not exist for the given caja."""


class ChequeAunNoLiquidableError(Exception):
    """The cheque's fecha de liquidación is still in the future."""


class ChequeYaLiquidadoError(Exception):
    """Raised when trying to liquidate or endorse a cheque that is no longer pending.

    A cheque that was already endorsed is also liquidated, so this single error covers
    "already liquidated" and "already endorsed".
    """


class CajaDestinoNotFoundError(Exception):
    """The destination caja of an endorsement does not exist."""


class EndoseDestinoInvalidoError(ValueError):
    """The destination caja of an endorsement is the origin caja or is archived."""


class MovimientoEndosadoError(Exception):
    """Endorsed cheques and the movements they generate are final: no edit / delete."""


ENDOSE_DESCRIPCION_MAX = 500


@dataclass(frozen=True)
class EndoseResult:
    """Both records touched by an endorsement."""

    cheque: Movimiento
    movimiento_destino: Movimiento


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
        fecha_override: datetime | None = None,  # T028: fecha manual a 09:00 AR (US3)
        instrumento: str = INSTRUMENTO_NINGUNO,
        fecha_liquidacion: date | None = None,
        endose_cheque_id: int | None = None,  # feature 011: set only by `endosar_cheque`
        user: Usuario,
    ) -> Movimiento:
        cleaned_description = descripcion.strip()
        if not cleaned_description:
            raise ValueError("descripcion no puede estar vacía")
        if instrumento not in VALID_INSTRUMENTOS:
            raise ValueError("instrumento inválido")

        if instrumento in INSTRUMENTOS_CHEQUE:
            if fecha_liquidacion is None:
                raise ValueError("fecha_liquidacion es obligatoria para cheque o echeque")
            return self._create_cheque_pendiente(
                caja_id=caja_id,
                descripcion=cleaned_description,
                monto=monto,
                tipo=tipo,
                moneda=moneda,
                instrumento=instrumento,
                fecha_liquidacion=fecha_liquidacion,
                fecha_override=fecha_override,
                user=user,
            )
        if fecha_liquidacion is not None:
            raise ValueError("fecha_liquidacion solo corresponde a un cheque o echeque")

        # Lock and fetch the last row of the *same currency stream* that impacts the
        # balance (pending cheques have no subtotal and never take part), ordered by the
        # effective date so back-dated movements are positioned correctly.
        last_movimiento = self.db.scalar(
            select(Movimiento)
            .where(
                Movimiento.caja_id == caja_id,
                Movimiento.moneda == moneda,
                Movimiento.subtotal.is_not(None),
            )
            .order_by(effective_date_expr().desc(), Movimiento.id.desc())
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
            instrumento=INSTRUMENTO_NINGUNO,
            subtotal=subtotal,
            created_by=user.id,
            fecha_override=fecha_override,  # T028: persisted; None keeps original behavior
            endose_cheque_id=endose_cheque_id,
        )
        self.db.add(movimiento)
        self.db.flush()
        if fecha_override is not None:
            # A back-dated (or future-dated) movement can land in the middle of the stream:
            # replay it so every stored subtotal matches the chronological order.
            self.recalculate_subtotals(caja_id, moneda=moneda)
        self.db.refresh(movimiento)
        return movimiento

    def _create_cheque_pendiente(
        self,
        *,
        caja_id: int,
        descripcion: str,
        monto: Decimal,
        tipo: str,
        moneda: str,
        instrumento: str,
        fecha_liquidacion: date,
        fecha_override: datetime | None,
        user: Usuario,
    ) -> Movimiento:
        """Create a PENDING cheque/echeque.

        It has no subtotal and never touches the (caja, moneda) stream: the stream is not
        read, locked or recalculated, so it cannot alter any balance (Principle I).
        """
        if tipo not in VALID_TIPOS:
            raise ValueError("tipo inválido: debe ser 'entrada' o 'salida'")
        movimiento = Movimiento(
            caja_id=caja_id,
            descripcion=descripcion,
            monto=monto,
            tipo=tipo,
            moneda=moneda,
            instrumento=instrumento,
            fecha_liquidacion=fecha_liquidacion,
            subtotal=None,
            created_by=user.id,
            fecha_override=fecha_override,  # fecha de carga manual (optional)
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
        moneda: str = "USD",
        fecha_override: datetime | None = None,  # T031: propagado a ambos movimientos
        user: "Usuario",
    ) -> "tuple[Movimiento, Movimiento]":
        """
        Create an atomic pair of movimientos with opposite tipos in the same currency.
        Both are flushed in the same transaction; the caller must commit.
        Returns (principal, complementario).

        `moneda` defaults to "USD" for backward-compatibility but accepts "ARS" as well.
        `fecha_override` is propagated to both movements when provided (US3).
        """
        principal = self.create_movimiento(
            caja_id=caja_id,
            descripcion=descripcion,
            monto=monto,
            tipo=tipo,
            moneda=moneda,
            fecha_override=fecha_override,
            user=user,
        )
        complementario_tipo = "salida" if tipo == "entrada" else "entrada"
        complementario = self.create_movimiento(
            caja_id=caja_id,
            descripcion=principal.descripcion,
            monto=monto,
            tipo=complementario_tipo,
            moneda=moneda,
            fecha_override=fecha_override,
            user=user,
        )
        return principal, complementario

    def liquidar_cheque(
        self,
        *,
        caja_id: int,
        movimiento_id: int,
        user: Usuario,
    ) -> Movimiento:
        """Liquidate a pending cheque/echeque: it starts to impact the balance.

        Lock order is always caja -> cheque row -> stream rows, so concurrent
        liquidations of the same caja are serialized and a double submit cannot count
        the cheque twice (the second one finds it already liquidated -> conflict).
        Everything happens in the caller's transaction: on any failure the caller rolls
        back and the cheque stays pending.
        """
        # FOR NO KEY UPDATE serializes liquidations of this caja without blocking the
        # foreign-key checks of concurrent inserts.
        self.db.scalar(
            select(Caja.id).where(Caja.id == caja_id).with_for_update(key_share=True)
        )
        cheque = self.db.scalar(
            select(Movimiento)
            .where(
                Movimiento.id == movimiento_id,
                Movimiento.caja_id == caja_id,
                Movimiento.instrumento.in_(INSTRUMENTOS_CHEQUE),
            )
            .with_for_update()
        )
        if cheque is None:
            raise MovimientoNotFoundError()
        if cheque.fecha_liquidado is not None:
            raise ChequeYaLiquidadoError()
        # Business rule: a cheque can only be settled once its fecha de liquidación has
        # arrived (today, Argentina calendar, or earlier). The UI greys the button out too,
        # but this is the authoritative check.
        if cheque.fecha_liquidacion is not None and cheque.fecha_liquidacion > today_ar():
            raise ChequeAunNoLiquidableError()

        now = datetime.now(timezone.utc)
        cheque.fecha_liquidado = now
        # CHECK ck_movimiento_subtotal_estado: a liquidated cheque must carry a subtotal in
        # the very same write. The value is provisional; the replay below computes the real
        # one in effective-date order (it also repairs any later-dated movement).
        cheque.subtotal = compute_subtotal(Decimal("0"), cheque.monto, cheque.tipo)
        cheque.updated_at = now
        cheque.updated_by = user.id
        self.db.flush()

        self.recalculate_subtotals(caja_id, moneda=cheque.moneda)
        self.db.refresh(cheque)
        return cheque

    def endosar_cheque(
        self,
        *,
        caja_id: int,
        movimiento_id: int,
        caja_destino_id: int,
        user: Usuario,
    ) -> EndoseResult:
        """Endorse a pending cheque to another caja (feature 011), atomically.

        1. The cheque is liquidated in its own caja (entrada adds / salida subtracts), with
           no check on its fecha de liquidación: an endorsement may happen at any time.
        2. A common movement with the INVERSE tipo, same moneda and monto is created in the
           destination caja (its description is generated here, never taken from the client).

        Lock order: both cajas by ascending id -> cheque row -> stream rows. The fixed
        caja order prevents deadlocks between crossed endorsements (A->B and B->A), and
        the cheque row lock makes a double submit find the cheque already liquidated.
        Nothing is committed here: on any failure the caller rolls back and the cheque
        stays pending with no movement in the destination caja.
        """
        if caja_destino_id == caja_id:
            raise EndoseDestinoInvalidoError("La caja destino debe ser distinta de la caja origen")

        cajas = {
            caja.id: caja
            for caja in self.db.scalars(
                select(Caja)
                .where(Caja.id.in_([caja_id, caja_destino_id]))
                .order_by(Caja.id.asc())
                .with_for_update(key_share=True)
            ).all()
        }
        caja_origen = cajas.get(caja_id)
        caja_destino = cajas.get(caja_destino_id)
        if caja_destino is None:
            raise CajaDestinoNotFoundError()
        if caja_destino.estado != "activa":
            raise EndoseDestinoInvalidoError("La caja destino debe estar activa")

        cheque = self.db.scalar(
            select(Movimiento)
            .where(
                Movimiento.id == movimiento_id,
                Movimiento.caja_id == caja_id,
                Movimiento.instrumento.in_(INSTRUMENTOS_CHEQUE),
            )
            .with_for_update()
        )
        if caja_origen is None or cheque is None:
            raise MovimientoNotFoundError()
        if cheque.fecha_liquidado is not None:
            raise ChequeYaLiquidadoError()

        now = datetime.now(timezone.utc)
        cheque.fecha_liquidado = now
        # Provisional subtotal required by ck_movimiento_subtotal_estado; replayed below.
        cheque.subtotal = compute_subtotal(Decimal("0"), cheque.monto, cheque.tipo)
        cheque.endosado_a_caja_id = caja_destino_id
        cheque.updated_at = now
        cheque.updated_by = user.id
        self.db.flush()

        movimiento_destino = self.create_movimiento(
            caja_id=caja_destino_id,
            descripcion=f"Endose cheque: {cheque.descripcion} (Caja {caja_origen.nombre})"[
                :ENDOSE_DESCRIPCION_MAX
            ],
            monto=cheque.monto,
            tipo="salida" if cheque.tipo == "entrada" else "entrada",
            moneda=cheque.moneda,
            endose_cheque_id=cheque.id,
            user=user,
        )

        self.recalculate_subtotals(caja_id, moneda=cheque.moneda)
        self.recalculate_subtotals(caja_destino_id, moneda=cheque.moneda)
        self.db.refresh(cheque)
        self.db.refresh(movimiento_destino)
        return EndoseResult(cheque=cheque, movimiento_destino=movimiento_destino)

    def recalculate_subtotals(self, caja_id: int, moneda: str = "ARS") -> None:
        """Recalculate subtotals for a single currency stream (caja_id, moneda).

        Only rows that take part in the stream (common movements and settled cheques) are
        replayed, in effective-date order. Pending cheques are left untouched.
        """
        movimientos = self.db.scalars(
            select(Movimiento)
            .where(
                Movimiento.caja_id == caja_id,
                Movimiento.moneda == moneda,
                impacta_saldo_expr(),
            )
            .order_by(effective_date_expr().asc(), Movimiento.id.asc())
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
        instrumento: str | None = None,
        fecha_liquidacion: date | None = None,
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
        if movimiento.bloqueado_por_endose:
            raise MovimientoEndosadoError()

        es_cheque = movimiento.instrumento in INSTRUMENTOS_CHEQUE
        pendiente = es_cheque and movimiento.fecha_liquidado is None

        # Instrument rules (checked before touching anything).
        if instrumento is not None:
            if instrumento not in INSTRUMENTOS_CHEQUE:
                raise ValueError("instrumento inválido: solo 'cheque' o 'echeque'")
            if not es_cheque:
                raise ValueError(
                    "un movimiento común no puede convertirse en cheque o echeque"
                )
        if fecha_liquidacion is not None:
            if not es_cheque:
                raise ValueError(
                    "fecha_liquidacion solo corresponde a un cheque o echeque"
                )
            if not pendiente:
                raise ValueError(
                    "la fecha de liquidación de un cheque liquidado no se puede editar"
                )
            if fecha_liquidacion <= today_ar():
                raise ValueError("fecha_liquidacion debe ser posterior a hoy")

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
        if instrumento is not None:
            movimiento.instrumento = instrumento
        if fecha_liquidacion is not None:
            movimiento.fecha_liquidacion = fecha_liquidacion

        # Detect whether the currency stream is changing before mutating.
        old_moneda = movimiento.moneda
        if moneda is not None and moneda != old_moneda:
            movimiento.moneda = moneda

        movimiento.updated_at = datetime.now(timezone.utc)
        movimiento.updated_by = user.id

        # The session runs with autoflush disabled: persist the edit first so the replay
        # queries below see the row in its new stream (otherwise a moneda change would
        # leave the moved row with a stale subtotal).
        self.db.flush()

        # A pending cheque does not impact any balance: nothing to replay (Principle I).
        if not pendiente:
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
    ) -> Movimiento:
        """Delete a movimiento and return it (already detached from the stream)."""
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
        if movimiento.bloqueado_por_endose:
            raise MovimientoEndosadoError()

        # Only rows that impact the balance require replaying their stream.
        impactaba_saldo = movimiento.subtotal is not None

        self.db.delete(movimiento)
        self.db.flush()
        if impactaba_saldo:
            self.recalculate_subtotals(caja_id, moneda=movimiento.moneda)
        return movimiento
