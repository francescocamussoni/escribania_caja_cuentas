"""
T019 — TDD: `MovimientoService.create_movimiento` para cheque/echeque (feature 010, US1).

Un cheque se crea PENDIENTE: subtotal NULL, sin leer ni bloquear el stream, sin
recalcular nada. La lógica es de dominio puro: se aísla la DB con mocks.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.movimiento_service import MovimientoService

FUTURE = date(2030, 1, 15)


def _service() -> tuple[MovimientoService, MagicMock]:
    db = MagicMock()
    db.scalar.return_value = None
    return MovimientoService(db=db), db


def _user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    return user


@pytest.mark.parametrize("instrumento", ["cheque", "echeque"])
def test_cheque_is_created_pending_without_subtotal(instrumento: str) -> None:
    service, db = _service()

    service.create_movimiento(
        caja_id=1,
        descripcion="Cheque cliente",
        monto=Decimal("500.00"),
        tipo="entrada",
        instrumento=instrumento,
        fecha_liquidacion=FUTURE,
        user=_user(),
    )

    created = db.add.call_args[0][0]
    assert created.instrumento == instrumento
    assert created.subtotal is None
    assert created.fecha_liquidacion == FUTURE
    assert created.fecha_liquidado is None


def test_cheque_does_not_lock_or_read_the_stream() -> None:
    service, db = _service()

    with patch.object(service, "recalculate_subtotals") as recalc:
        service.create_movimiento(
            caja_id=1,
            descripcion="Cheque",
            monto=Decimal("10.00"),
            tipo="salida",
            instrumento="echeque",
            fecha_liquidacion=FUTURE,
            user=_user(),
        )

    db.scalar.assert_not_called()
    recalc.assert_not_called()


def test_cheque_honors_fecha_override_as_fecha_de_carga_without_recalculating() -> None:
    service, db = _service()
    override = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)

    with patch.object(service, "recalculate_subtotals") as recalc:
        service.create_movimiento(
            caja_id=1,
            descripcion="Cheque",
            monto=Decimal("10.00"),
            tipo="entrada",
            instrumento="cheque",
            fecha_liquidacion=FUTURE,
            fecha_override=override,
            user=_user(),
        )

    assert db.add.call_args[0][0].fecha_override == override
    recalc.assert_not_called()  # un pendiente no toca el stream aunque tenga fecha_override


def test_common_movement_keeps_instrumento_ninguno() -> None:
    service, db = _service()

    service.create_movimiento(
        caja_id=1, descripcion="x", monto=Decimal("10.00"), tipo="entrada", user=_user()
    )

    created = db.add.call_args[0][0]
    assert created.instrumento == "ninguno"
    assert created.subtotal == Decimal("10.00")
    assert created.fecha_liquidacion is None


def test_cheque_requires_fecha_liquidacion() -> None:
    service, _ = _service()
    with pytest.raises(ValueError):
        service.create_movimiento(
            caja_id=1,
            descripcion="x",
            monto=Decimal("10.00"),
            tipo="entrada",
            instrumento="cheque",
            user=_user(),
        )


def test_common_movement_rejects_fecha_liquidacion() -> None:
    service, _ = _service()
    with pytest.raises(ValueError):
        service.create_movimiento(
            caja_id=1,
            descripcion="x",
            monto=Decimal("10.00"),
            tipo="entrada",
            fecha_liquidacion=FUTURE,
            user=_user(),
        )


def test_invalid_instrumento_is_rejected() -> None:
    service, _ = _service()
    with pytest.raises(ValueError):
        service.create_movimiento(
            caja_id=1,
            descripcion="x",
            monto=Decimal("10.00"),
            tipo="entrada",
            instrumento="pagare",
            fecha_liquidacion=FUTURE,
            user=_user(),
        )
