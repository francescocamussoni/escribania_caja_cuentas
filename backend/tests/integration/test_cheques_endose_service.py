"""
T009 — TDD: concurrencia e integridad de los streams en el endose (feature 011, US1).

Usa sesiones reales con commit (como `cheque_helpers`) para ejercitar locks de Postgres.
Cada test crea cajas nuevas y vacías.
"""

import threading
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.services.movimiento_service import (
    ChequeYaLiquidadoError,
    MovimientoService,
)
from app.services.saldo_service import get_saldo_actual

FUTURO = date(2030, 1, 15)


def _new_caja() -> int:
    nombre = f"Endose conc {uuid4().hex[:12]}"
    with SessionLocal() as session:
        caja = Caja(nombre=nombre, slug=nombre.lower().replace(" ", "-"), estado="activa")
        session.add(caja)
        session.commit()
        return caja.id


def _new_cheque(caja_id: int, *, tipo: str = "entrada", monto: str = "100.00") -> int:
    with SessionLocal() as session:
        user = session.scalar(select(Usuario).where(Usuario.username == "admin"))
        assert user is not None
        cheque = MovimientoService(session).create_movimiento(
            caja_id=caja_id,
            descripcion="cheque concurrente",
            monto=Decimal(monto),
            tipo=tipo,
            moneda="ARS",
            instrumento="cheque",
            fecha_liquidacion=FUTURO,
            user=user,
        )
        session.commit()
        return cheque.id


def _saldo(caja_id: int) -> Decimal:
    with SessionLocal() as session:
        return get_saldo_actual(session, caja_id, "ARS")


def _endosar(caja_id: int, cheque_id: int, destino_id: int, results: list, barrier) -> None:
    with SessionLocal() as session:
        user = session.scalar(select(Usuario).where(Usuario.username == "admin"))
        assert user is not None
        barrier.wait(timeout=10)
        try:
            MovimientoService(session).endosar_cheque(
                caja_id=caja_id, movimiento_id=cheque_id, caja_destino_id=destino_id, user=user
            )
            session.commit()
            results.append("ok")
        except ChequeYaLiquidadoError:
            session.rollback()
            results.append("conflict")
        except Exception as exc:  # pragma: no cover - surfaced by the assertions below
            session.rollback()
            results.append(f"error:{type(exc).__name__}:{exc}")


def test_double_endose_of_same_cheque_only_counts_once() -> None:
    origen, destino = _new_caja(), _new_caja()
    cheque_id = _new_cheque(origen, monto="100.00")

    results: list[str] = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_endosar, args=(origen, cheque_id, destino, results, barrier))
        for _ in range(2)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sorted(results) == ["conflict", "ok"], results
    assert _saldo(origen) == Decimal("100.00")
    assert _saldo(destino) == Decimal("-100.00")
    with SessionLocal() as session:
        generated = session.scalars(
            select(Movimiento).where(Movimiento.endose_cheque_id == cheque_id)
        ).all()
        assert len(generated) == 1


def test_crossed_endorsements_do_not_deadlock() -> None:
    caja_a, caja_b = _new_caja(), _new_caja()
    cheque_a = _new_cheque(caja_a, tipo="entrada", monto="100.00")
    cheque_b = _new_cheque(caja_b, tipo="entrada", monto="40.00")

    results: list[str] = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_endosar, args=(caja_a, cheque_a, caja_b, results, barrier)),
        threading.Thread(target=_endosar, args=(caja_b, cheque_b, caja_a, results, barrier)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert all(not t.is_alive() for t in threads), "deadlock: threads did not finish"
    assert results == ["ok", "ok"], results
    # A: +100 (own cheque) -40 (endose of B's cheque) ; B: +40 -100
    assert _saldo(caja_a) == Decimal("60.00")
    assert _saldo(caja_b) == Decimal("-60.00")


def test_subtotals_match_chronological_replay_after_endose() -> None:
    origen, destino = _new_caja(), _new_caja()
    with SessionLocal() as session:
        user = session.scalar(select(Usuario).where(Usuario.username == "admin"))
        assert user is not None
        service = MovimientoService(session)
        # A later-dated manual movement already sits in the destination stream.
        futuro = datetime.now(timezone.utc) + timedelta(days=5)
        service.create_movimiento(
            caja_id=destino,
            descripcion="adelantado",
            monto=Decimal("1000.00"),
            tipo="entrada",
            moneda="ARS",
            fecha_override=futuro,
            user=user,
        )
        session.commit()
    cheque_id = _new_cheque(origen, tipo="entrada", monto="300.00")

    results: list[str] = []
    _endosar(origen, cheque_id, destino, results, threading.Barrier(1))
    assert results == ["ok"]

    for caja_id in (origen, destino):
        with SessionLocal() as session:
            rows = session.scalars(
                select(Movimiento)
                .where(Movimiento.caja_id == caja_id)
                .order_by(
                    Movimiento.fecha_liquidado.asc().nulls_last(),
                    Movimiento.id.asc(),
                )
            ).all()
            # Replay the stored subtotals in effective-date order.
            rows = sorted(rows, key=lambda m: (m.fecha_efectiva, m.id))
            running = Decimal("0")
            for row in rows:
                running += row.monto if row.tipo == "entrada" else -row.monto
                assert row.subtotal == running
            assert _saldo(caja_id) == running
