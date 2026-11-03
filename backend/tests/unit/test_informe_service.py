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


def test_fetch_saldo_ars_and_usd_use_the_saldo_service_sum() -> None:
    """Current balances are the SUM of rows that impact the balance (not a stored subtotal)."""
    mock_db = MagicMock()
    mock_db.scalar.side_effect = [Decimal("999.50"), Decimal("-20.00")]
    service = InformeService(mock_db)

    assert service.fetch_saldo_ars(2) == Decimal("999.50")
    assert service.fetch_saldo_usd(2) == Decimal("-20.00")


def test_fetch_saldo_without_movimientos_returns_zero() -> None:
    mock_db = MagicMock()
    mock_db.scalar.return_value = 0
    service = InformeService(mock_db)

    assert service.fetch_saldo_ars(2) == Decimal("0.00")
    assert service.fetch_saldo_usd(2) == Decimal("0.00")


def _compiled(statement) -> str:
    from sqlalchemy.dialects import postgresql

    return str(
        statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def test_fetch_movimientos_informe_excludes_pending_and_uses_effective_date() -> None:
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []
    service = InformeService(mock_db)

    service.fetch_movimientos_informe(
        caja_id=2, date_from=date(2026, 3, 1), date_to=date(2026, 3, 31)
    )

    sql = _compiled(mock_db.scalars.call_args[0][0])
    where, order_by = sql.split("ORDER BY")
    assert "movimiento.subtotal IS NOT NULL" in where
    # Range filter and ordering both use the effective date.
    assert "fecha_liquidado" in where and "fecha_override" in where
    assert "fecha_liquidado" in order_by and "fecha_override" in order_by
    assert "DESC" in order_by


def test_compute_saldo_cierre_uses_the_effective_date() -> None:
    # `a` was created first but liquidated last: it is the closing row.
    a = _movimiento(
        movimiento_id=1,
        created_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        subtotal=Decimal("300.00"),
    )
    a.moneda = "ARS"
    a.instrumento = "cheque"
    a.fecha_liquidado = datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc)
    b = _movimiento(
        movimiento_id=2,
        created_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
        subtotal=Decimal("200.00"),
    )
    b.moneda = "ARS"

    assert compute_saldo_cierre([a, b]) == Decimal("300.00")
    assert InformeService.compute_saldo_cierre_by_moneda([a, b], "ARS") == Decimal("300.00")
    assert InformeService.compute_saldo_cierre_by_moneda([a, b], "USD") is None


def test_fetch_cheques_pendientes_returns_items_and_total_with_a_cap() -> None:
    cheque = _movimiento(
        movimiento_id=9,
        created_at=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
        subtotal=Decimal("0"),
    )
    mock_db = MagicMock()
    mock_db.scalar.return_value = 1500
    mock_db.scalars.return_value.all.return_value = [cheque]
    service = InformeService(mock_db)

    items, total = service.fetch_cheques_pendientes(2)

    assert items == [cheque]
    assert total == 1500
    sql = _compiled(mock_db.scalars.call_args[0][0])
    assert "LIMIT 1000" in sql
    where, order_by = sql.split("ORDER BY")
    assert "fecha_liquidado IS NULL" in where
    assert "fecha_liquidacion ASC" in order_by


def test_fetch_saldo_futuro_delegates_to_the_shared_projection() -> None:
    from unittest.mock import patch

    mock_db = MagicMock()
    service = InformeService(mock_db)

    with patch(
        "app.services.informe_service.build_saldo_futuro", return_value={"ARS": (Decimal("1"), [])}
    ) as build:
        result = service.fetch_saldo_futuro(2, hoy=date(2026, 10, 21))

    build.assert_called_once_with(mock_db, 2, date(2026, 10, 21))
    assert result == {"ARS": (Decimal("1"), [])}


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
