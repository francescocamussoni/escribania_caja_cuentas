from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models.movimiento import Movimiento
from app.models.plazo_fijo import PlazoFijo
from app.services.informe_service import (
    InformeService,
    compute_resumen_plazos_filtrado,
    compute_saldo_cierre,
)


def _movimiento(
    *,
    movimiento_id: int,
    created_at: datetime,
    subtotal: Decimal,
    caja_id: int = 2,
) -> Movimiento:
    movimiento = Movimiento(
        caja_id=caja_id,
        descripcion=f"Movimiento {movimiento_id}",
        monto=Decimal("100.00"),
        tipo="entrada",
        subtotal=subtotal,
        created_by=1,
    )
    movimiento.id = movimiento_id
    movimiento.created_at = created_at
    return movimiento


def test_compute_saldo_cierre_returns_latest_subtotal() -> None:
    older = _movimiento(
        movimiento_id=1,
        created_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        subtotal=Decimal("100.00"),
    )
    newer = _movimiento(
        movimiento_id=2,
        created_at=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
        subtotal=Decimal("250.00"),
    )

    assert compute_saldo_cierre([older, newer]) == Decimal("250.00")


def test_compute_saldo_cierre_empty_period_returns_none() -> None:
    assert compute_saldo_cierre([]) is None


def test_fetch_movimientos_informe_returns_query_results() -> None:
    movimiento = _movimiento(
        movimiento_id=3,
        created_at=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
        subtotal=Decimal("300.00"),
    )
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [movimiento]
    service = InformeService(mock_db)

    result = service.fetch_movimientos_informe(
        caja_id=2,
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 31),
    )

    assert result == [movimiento]
    mock_db.scalars.assert_called_once()


def test_fetch_saldo_actual_returns_last_subtotal() -> None:
    movimiento = _movimiento(
        movimiento_id=4,
        created_at=datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc),
        subtotal=Decimal("999.50"),
    )
    mock_db = MagicMock()
    mock_db.scalar.return_value = movimiento
    service = InformeService(mock_db)

    assert service.fetch_saldo_actual(2) == Decimal("999.50")


def test_fetch_saldo_actual_without_movimientos_returns_zero() -> None:
    mock_db = MagicMock()
    mock_db.scalar.return_value = None
    service = InformeService(mock_db)

    assert service.fetch_saldo_actual(2) == Decimal("0")


def _plazo_fijo(
    *,
    plazo_id: int,
    monto_ingresado: Decimal,
    monto_a_vencimiento: Decimal,
    fecha_vencimiento: date,
    created_at: datetime,
    caja_id: int = 5,
) -> PlazoFijo:
    plazo = PlazoFijo(
        caja_id=caja_id,
        monto_ingresado=monto_ingresado,
        monto_a_vencimiento=monto_a_vencimiento,
        fecha_vencimiento=fecha_vencimiento,
        created_by=1,
    )
    plazo.id = plazo_id
    plazo.created_at = created_at
    return plazo


def test_fetch_plazos_informe_returns_query_results() -> None:
    plazo = _plazo_fijo(
        plazo_id=1,
        monto_ingresado=Decimal("1000.00"),
        monto_a_vencimiento=Decimal("1100.00"),
        fecha_vencimiento=date(2026, 12, 31),
        created_at=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
    )
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [plazo]
    service = InformeService(mock_db)

    result = service.fetch_plazos_informe(
        caja_id=5,
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 31),
    )

    assert result == [plazo]
    mock_db.scalars.assert_called_once()


def test_compute_resumen_plazos_filtrado_only_active_in_period() -> None:
    activo = _plazo_fijo(
        plazo_id=1,
        monto_ingresado=Decimal("1000.00"),
        monto_a_vencimiento=Decimal("1200.00"),
        fecha_vencimiento=date(2026, 12, 31),
        created_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
    )
    vencido = _plazo_fijo(
        plazo_id=2,
        monto_ingresado=Decimal("500.00"),
        monto_a_vencimiento=Decimal("550.00"),
        fecha_vencimiento=date(2026, 1, 15),
        created_at=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc),
    )

    resumen = compute_resumen_plazos_filtrado(
        [activo, vencido],
        reference_today=date(2026, 8, 6),
    )

    assert resumen.total_monto_ingresado_activos == Decimal("1000.00")
    assert resumen.total_monto_a_vencimiento_activos == Decimal("1200.00")


def test_compute_resumen_plazos_filtrado_empty_period() -> None:
    resumen = compute_resumen_plazos_filtrado([], reference_today=date(2026, 8, 6))

    assert resumen.total_monto_ingresado_activos == Decimal("0")
    assert resumen.total_monto_a_vencimiento_activos == Decimal("0")
