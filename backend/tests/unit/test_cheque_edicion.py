"""
T064 — TDD: edición y eliminación de cheques en `MovimientoService` (feature 010, US5).

Reglas (research §7): un cheque PENDIENTE no impacta saldo, así que editarlo o eliminarlo
nunca recalcula un stream; un cheque LIQUIDADO sigue las reglas actuales (cascada).
`instrumento` solo cambia entre cheque↔echeque; `fecha_liquidacion` solo en pendientes.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.models.movimiento import Movimiento
from app.services.movimiento_service import MovimientoNotFoundError, MovimientoService

FUTURO = date(2999, 1, 1)


def _user() -> MagicMock:
    user = MagicMock()
    user.id = 9
    return user


def _mov(
    *,
    instrumento: str = "cheque",
    liquidado: bool = False,
    moneda: str = "ARS",
    tipo: str = "entrada",
    monto: str = "100.00",
) -> Movimiento:
    common = instrumento == "ninguno"
    return Movimiento(
        id=5,
        caja_id=1,
        descripcion="original",
        monto=Decimal(monto),
        tipo=tipo,
        moneda=moneda,
        instrumento=instrumento,
        fecha_liquidacion=None if common else date(2030, 1, 15),
        fecha_liquidado=datetime(2026, 5, 1, tzinfo=timezone.utc) if liquidado else None,
        subtotal=Decimal("100.00") if (common or liquidado) else None,
        created_by=1,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _service(mov: Movimiento | None) -> tuple[MovimientoService, MagicMock]:
    db = MagicMock()
    db.scalar.return_value = mov
    return MovimientoService(db=db), db


# ---------------------------------------------------------------------------
# update — pendiente
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"monto": Decimal("250.00")},
        {"tipo": "salida"},
        {"moneda": "USD"},
        {"descripcion": "nueva"},
        {"instrumento": "echeque"},
        {"fecha_liquidacion": FUTURO},
    ],
)
def test_pending_cheque_edit_never_recalculates_any_stream(changes: dict) -> None:
    mov = _mov()
    service, _ = _service(mov)

    with patch.object(service, "recalculate_subtotals") as recalc:
        service.update_movimiento(caja_id=1, movimiento_id=5, user=_user(), **changes)

    recalc.assert_not_called()
    assert mov.subtotal is None
    assert mov.updated_by == 9
    assert mov.updated_at is not None


def test_pending_cheque_edit_applies_the_changes() -> None:
    mov = _mov()
    service, _ = _service(mov)

    service.update_movimiento(
        caja_id=1,
        movimiento_id=5,
        user=_user(),
        monto=Decimal("7.50"),
        tipo="salida",
        moneda="USD",
        instrumento="echeque",
        fecha_liquidacion=FUTURO,
    )

    assert (mov.monto, mov.tipo, mov.moneda) == (Decimal("7.50"), "salida", "USD")
    assert mov.instrumento == "echeque"
    assert mov.fecha_liquidacion == FUTURO


def test_pending_fecha_liquidacion_must_be_after_today() -> None:
    mov = _mov()
    service, _ = _service(mov)

    with patch("app.services.movimiento_service.today_ar", return_value=date(2026, 10, 21)):
        with pytest.raises(ValueError):
            service.update_movimiento(
                caja_id=1,
                movimiento_id=5,
                user=_user(),
                fecha_liquidacion=date(2026, 10, 21),
            )

    assert mov.fecha_liquidacion == date(2030, 1, 15)


# ---------------------------------------------------------------------------
# update — reglas de instrumento / fecha de liquidación
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "changes", [{"instrumento": "cheque"}, {"fecha_liquidacion": FUTURO}]
)
def test_common_movement_cannot_receive_instrument_fields(changes: dict) -> None:
    mov = _mov(instrumento="ninguno")
    service, _ = _service(mov)

    with patch.object(service, "recalculate_subtotals") as recalc:
        with pytest.raises(ValueError):
            service.update_movimiento(caja_id=1, movimiento_id=5, user=_user(), **changes)

    recalc.assert_not_called()
    assert mov.instrumento == "ninguno"
    assert mov.fecha_liquidacion is None


def test_liquidated_cheque_fecha_liquidacion_is_not_editable() -> None:
    mov = _mov(liquidado=True)
    service, _ = _service(mov)

    with pytest.raises(ValueError):
        service.update_movimiento(
            caja_id=1, movimiento_id=5, user=_user(), fecha_liquidacion=FUTURO
        )

    assert mov.fecha_liquidacion == date(2030, 1, 15)


def test_liquidated_cheque_can_switch_between_cheque_and_echeque() -> None:
    mov = _mov(liquidado=True)
    service, _ = _service(mov)

    with patch.object(service, "recalculate_subtotals"):
        service.update_movimiento(
            caja_id=1, movimiento_id=5, user=_user(), instrumento="echeque"
        )

    assert mov.instrumento == "echeque"


def test_invalid_instrumento_value_is_rejected_by_the_service() -> None:
    mov = _mov()
    service, _ = _service(mov)

    with pytest.raises(ValueError):
        service.update_movimiento(
            caja_id=1, movimiento_id=5, user=_user(), instrumento="ninguno"
        )

    assert mov.instrumento == "cheque"


# ---------------------------------------------------------------------------
# update — liquidado: cascada
# ---------------------------------------------------------------------------


def test_liquidated_cheque_edit_recalculates_its_stream() -> None:
    mov = _mov(liquidado=True)
    service, _ = _service(mov)

    with patch.object(service, "recalculate_subtotals") as recalc:
        service.update_movimiento(
            caja_id=1, movimiento_id=5, user=_user(), monto=Decimal("90.00")
        )

    recalc.assert_called_once_with(1, moneda="ARS")


def test_liquidated_cheque_moneda_change_recalculates_both_streams() -> None:
    mov = _mov(liquidado=True, moneda="ARS")
    service, _ = _service(mov)

    with patch.object(service, "recalculate_subtotals") as recalc:
        service.update_movimiento(caja_id=1, movimiento_id=5, user=_user(), moneda="USD")

    assert [c.kwargs["moneda"] for c in recalc.call_args_list] == ["USD", "ARS"]


def test_common_movement_edit_still_recalculates() -> None:
    mov = _mov(instrumento="ninguno")
    service, _ = _service(mov)

    with patch.object(service, "recalculate_subtotals") as recalc:
        service.update_movimiento(
            caja_id=1, movimiento_id=5, user=_user(), monto=Decimal("1.00")
        )

    recalc.assert_called_once_with(1, moneda="ARS")


def test_update_missing_movimiento_raises_not_found() -> None:
    service, _ = _service(None)

    with pytest.raises(MovimientoNotFoundError):
        service.update_movimiento(caja_id=1, movimiento_id=5, user=_user(), monto=Decimal("1"))


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_deleting_a_pending_cheque_does_not_recalculate() -> None:
    mov = _mov()
    service, db = _service(mov)

    with patch.object(service, "recalculate_subtotals") as recalc:
        service.delete_movimiento(caja_id=1, movimiento_id=5, user=_user())

    db.delete.assert_called_once_with(mov)
    recalc.assert_not_called()


def test_deleting_a_liquidated_cheque_recalculates_its_stream() -> None:
    mov = _mov(liquidado=True, moneda="USD")
    service, db = _service(mov)

    with patch.object(service, "recalculate_subtotals") as recalc:
        service.delete_movimiento(caja_id=1, movimiento_id=5, user=_user())

    db.delete.assert_called_once_with(mov)
    recalc.assert_called_once_with(1, moneda="USD")


def test_deleting_a_common_movement_still_recalculates() -> None:
    mov = _mov(instrumento="ninguno")
    service, _ = _service(mov)

    with patch.object(service, "recalculate_subtotals") as recalc:
        service.delete_movimiento(caja_id=1, movimiento_id=5, user=_user())

    recalc.assert_called_once_with(1, moneda="ARS")


def test_delete_returns_the_deleted_instrumento_for_logging() -> None:
    mov = _mov(instrumento="echeque")
    service, _ = _service(mov)

    result = service.delete_movimiento(caja_id=1, movimiento_id=5, user=_user())

    assert result.instrumento == "echeque"
