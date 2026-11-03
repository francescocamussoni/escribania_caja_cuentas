"""
T035 — TDD: `MovimientoService.liquidar_cheque` (feature 010, US2).

Dominio puro: la DB se aísla con mocks y el "stream" se simula devolviendo, desde
`db.scalars(...).all()`, las filas que participan del saldo. Así se ejercita el
`recalculate_subtotals` real y se verifica el subtotal resultante del cheque.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.models.movimiento import Movimiento
from app.services.movimiento_service import (
    ChequeYaLiquidadoError,
    MovimientoNotFoundError,
    MovimientoService,
)


def _user() -> MagicMock:
    user = MagicMock()
    user.id = 7
    return user


def _cheque(
    *,
    tipo: str = "entrada",
    monto: str = "100.00",
    liquidado: datetime | None = None,
    fecha: date = date(2020, 1, 15),
) -> Movimiento:
    return Movimiento(
        id=50,
        caja_id=1,
        descripcion="cheque",
        monto=Decimal(monto),
        tipo=tipo,
        moneda="ARS",
        instrumento="cheque",
        fecha_liquidacion=fecha,
        fecha_liquidado=liquidado,
        subtotal=None if liquidado is None else Decimal("0"),
        created_by=1,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _common(*, id: int, tipo: str, monto: str, subtotal: str) -> Movimiento:
    return Movimiento(
        id=id,
        caja_id=1,
        descripcion="comun",
        monto=Decimal(monto),
        tipo=tipo,
        moneda="ARS",
        instrumento="ninguno",
        subtotal=Decimal(subtotal),
        created_by=1,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _service(cheque: Movimiento | None, stream: list[Movimiento]) -> tuple[MovimientoService, MagicMock]:
    db = MagicMock()
    # 1st scalar = caja lock, 2nd scalar = cheque row
    db.scalar.side_effect = [1, cheque]
    db.scalars.return_value.all.return_value = stream
    return MovimientoService(db=db), db


def test_entrada_cheque_adds_to_the_stream() -> None:
    cheque = _cheque(tipo="entrada", monto="30.00")
    prev = _common(id=1, tipo="entrada", monto="100.00", subtotal="100.00")
    service, _ = _service(cheque, [prev, cheque])

    service.liquidar_cheque(caja_id=1, movimiento_id=50, user=_user())

    assert cheque.subtotal == Decimal("130.00")


def test_salida_cheque_subtracts_from_the_stream() -> None:
    cheque = _cheque(tipo="salida", monto="30.00")
    prev = _common(id=1, tipo="entrada", monto="100.00", subtotal="100.00")
    service, _ = _service(cheque, [prev, cheque])

    service.liquidar_cheque(caja_id=1, movimiento_id=50, user=_user())

    assert cheque.subtotal == Decimal("70.00")


def test_sets_fecha_liquidado_now_and_audit_fields() -> None:
    cheque = _cheque()
    service, _ = _service(cheque, [cheque])
    before = datetime.now(timezone.utc)

    service.liquidar_cheque(caja_id=1, movimiento_id=50, user=_user())

    assert cheque.fecha_liquidado is not None
    assert before - timedelta(seconds=1) <= cheque.fecha_liquidado <= datetime.now(timezone.utc)
    assert cheque.updated_by == 7
    assert cheque.updated_at is not None


def test_future_dated_manual_movement_is_replayed_after_the_cheque() -> None:
    """The cheque is placed by effective date; a later movement is recomputed after it."""
    cheque = _cheque(tipo="entrada", monto="50.00")
    futuro = _common(id=2, tipo="salida", monto="20.00", subtotal="-20.00")
    # Stream order by effective date: cheque (liquidado now) first, future movement last.
    service, _ = _service(cheque, [cheque, futuro])

    service.liquidar_cheque(caja_id=1, movimiento_id=50, user=_user())

    assert cheque.subtotal == Decimal("50.00")
    assert futuro.subtotal == Decimal("30.00")


def test_recalculates_only_the_cheque_stream() -> None:
    cheque = _cheque()
    service, _ = _service(cheque, [cheque])

    with patch.object(service, "recalculate_subtotals") as recalc:
        service.liquidar_cheque(caja_id=1, movimiento_id=50, user=_user())

    recalc.assert_called_once_with(1, moneda="ARS")


def test_flushes_the_cheque_with_a_subtotal_before_recalculating() -> None:
    """CHECK ck_movimiento_subtotal_estado: fecha_liquidado and subtotal go together."""
    cheque = _cheque()
    service, db = _service(cheque, [cheque])
    seen: dict[str, object] = {}

    def spy_flush() -> None:
        seen.setdefault("subtotal_at_first_flush", cheque.subtotal)
        seen.setdefault("liquidado_at_first_flush", cheque.fecha_liquidado)

    db.flush.side_effect = spy_flush

    service.liquidar_cheque(caja_id=1, movimiento_id=50, user=_user())

    assert seen["subtotal_at_first_flush"] is not None
    assert seen["liquidado_at_first_flush"] is not None


def test_already_liquidated_raises_conflict_and_does_not_touch_the_stream() -> None:
    cheque = _cheque(liquidado=datetime(2026, 5, 1, tzinfo=timezone.utc))
    service, _ = _service(cheque, [cheque])

    with patch.object(service, "recalculate_subtotals") as recalc:
        with pytest.raises(ChequeYaLiquidadoError):
            service.liquidar_cheque(caja_id=1, movimiento_id=50, user=_user())

    recalc.assert_not_called()
    assert cheque.fecha_liquidado == datetime(2026, 5, 1, tzinfo=timezone.utc)


def test_missing_common_or_foreign_movement_raises_not_found() -> None:
    """The lookup filters by caja and cheque/echeque: no row means not found."""
    service, _ = _service(None, [])

    with pytest.raises(MovimientoNotFoundError):
        service.liquidar_cheque(caja_id=1, movimiento_id=999, user=_user())


def test_failure_while_recalculating_propagates_so_the_caller_rolls_back() -> None:
    cheque = _cheque()
    service, _ = _service(cheque, [cheque])

    with patch.object(service, "recalculate_subtotals", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            service.liquidar_cheque(caja_id=1, movimiento_id=50, user=_user())


# ---------------------------------------------------------------------------
# Regla: solo se puede liquidar cuando llegó la fecha de liquidación
# ---------------------------------------------------------------------------

from datetime import timedelta  # noqa: E402

from app.core.dates import today_ar  # noqa: E402
from app.services.movimiento_service import ChequeAunNoLiquidableError  # noqa: E402


def test_cannot_liquidate_before_the_fecha_de_liquidacion() -> None:
    cheque = _cheque(fecha=today_ar() + timedelta(days=1))
    service, _ = _service(cheque, [cheque])

    with pytest.raises(ChequeAunNoLiquidableError):
        service.liquidar_cheque(caja_id=1, movimiento_id=50, user=_user())

    assert cheque.fecha_liquidado is None
    assert cheque.subtotal is None


def test_can_liquidate_on_the_fecha_de_liquidacion_itself() -> None:
    cheque = _cheque(fecha=today_ar())
    service, _ = _service(cheque, [cheque])

    service.liquidar_cheque(caja_id=1, movimiento_id=50, user=_user())

    assert cheque.fecha_liquidado is not None
    assert cheque.subtotal == Decimal("100.00")
