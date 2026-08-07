from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.movimiento import Movimiento
from app.models.plazo_fijo import PlazoFijo
from app.services.pdf_informe_renderer import (
    InformeCajaMetadata,
    InformePlazoFijoMetadata,
    render_caja_pdf,
    render_plazo_fijo_pdf,
)
from app.services.plazo_fijo_service import PlazosFijosResumen


def _movimiento(
    *,
    descripcion: str,
    monto: Decimal,
    tipo: str,
    subtotal: Decimal,
    created_at: datetime,
    movimiento_id: int = 1,
) -> Movimiento:
    movimiento = Movimiento(
        caja_id=2,
        descripcion=descripcion,
        monto=monto,
        tipo=tipo,
        subtotal=subtotal,
        created_by=1,
    )
    movimiento.id = movimiento_id
    movimiento.created_at = created_at
    return movimiento


def test_render_caja_pdf_includes_header_signs_and_dual_saldos() -> None:
    movimiento = _movimiento(
        descripcion="Cobro cliente",
        monto=Decimal("1500.00"),
        tipo="entrada",
        subtotal=Decimal("1500.00"),
        created_at=datetime(2026, 3, 10, 14, 30, tzinfo=timezone.utc),
    )
    metadata = InformeCajaMetadata(
        caja_nombre="Ebel",
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 31),
        generated_at=datetime(2026, 3, 31, 18, 0, tzinfo=timezone.utc),
    )

    pdf_bytes = render_caja_pdf(
        metadata=metadata,
        movimientos=[movimiento],
        saldo_cierre=Decimal("1500.00"),
        saldo_actual=Decimal("2000.00"),
        compress=False,
    )

    assert pdf_bytes.startswith(b"%PDF")
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
    assert "Informe de Caja" in pdf_text
    assert "Ebel" in pdf_text
    assert "Entrada +1500.00" in pdf_text
    assert "Saldo al cierre del per" in pdf_text
    assert "1500.00" in pdf_text
    assert "Saldo actual" in pdf_text
    assert "2000.00" in pdf_text


def test_render_caja_pdf_salida_uses_minus_sign() -> None:
    movimiento = _movimiento(
        descripcion="Pago proveedor",
        monto=Decimal("500.00"),
        tipo="salida",
        subtotal=Decimal("500.00"),
        created_at=datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc),
    )
    metadata = InformeCajaMetadata(
        caja_nombre="Ebel",
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 31),
        generated_at=datetime(2026, 3, 31, 18, 0, tzinfo=timezone.utc),
    )

    pdf_bytes = render_caja_pdf(
        metadata=metadata,
        movimientos=[movimiento],
        saldo_cierre=Decimal("500.00"),
        saldo_actual=Decimal("500.00"),
        compress=False,
    )
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
    assert "Salida -500.00" in pdf_text


def test_render_caja_pdf_empty_period_shows_message_without_cierre() -> None:
    metadata = InformeCajaMetadata(
        caja_nombre="Ebel",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        generated_at=datetime(2026, 1, 31, 12, 0, tzinfo=timezone.utc),
    )

    pdf_bytes = render_caja_pdf(
        metadata=metadata,
        movimientos=[],
        saldo_cierre=None,
        saldo_actual=Decimal("750.00"),
        compress=False,
    )
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")

    assert "No hay movimientos en el per" in pdf_text
    assert "Saldo al cierre del per" not in pdf_text
    assert "Saldo actual" in pdf_text
    assert "750.00" in pdf_text


def _plazo_fijo(
    *,
    plazo_id: int,
    monto_ingresado: Decimal,
    monto_a_vencimiento: Decimal,
    fecha_vencimiento: date,
) -> PlazoFijo:
    plazo = PlazoFijo(
        caja_id=5,
        monto_ingresado=monto_ingresado,
        monto_a_vencimiento=monto_a_vencimiento,
        fecha_vencimiento=fecha_vencimiento,
        created_by=1,
    )
    plazo.id = plazo_id
    plazo.created_at = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    return plazo


def test_render_plazo_fijo_pdf_includes_resumen_and_columns() -> None:
    plazo = _plazo_fijo(
        plazo_id=1,
        monto_ingresado=Decimal("100000.00"),
        monto_a_vencimiento=Decimal("105000.00"),
        fecha_vencimiento=date(2026, 12, 31),
    )
    metadata = InformePlazoFijoMetadata(
        caja_nombre="Gabriel",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 12, 31),
        generated_at=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
    )
    resumen = PlazosFijosResumen(
        total_monto_ingresado_activos=Decimal("100000.00"),
        total_monto_a_vencimiento_activos=Decimal("105000.00"),
    )

    pdf_bytes = render_plazo_fijo_pdf(
        metadata=metadata,
        plazos=[plazo],
        resumen=resumen,
        compress=False,
    )

    assert pdf_bytes.startswith(b"%PDF")
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
    assert "Informe de Plazos Fijos" in pdf_text
    assert "Gabriel" in pdf_text
    assert "Dinero ingresado en plazos activos" in pdf_text
    assert "Dinero a cobrar al vencer" in pdf_text
    assert "100000.00" in pdf_text
    assert "105000.00" in pdf_text
    assert "Monto ingresado" in pdf_text
    assert "Fecha vencimiento" in pdf_text
    assert "31/12/2026" in pdf_text


def test_render_plazo_fijo_pdf_orders_rows_by_vencimiento() -> None:
    plazo_tarde = _plazo_fijo(
        plazo_id=1,
        monto_ingresado=Decimal("2000.00"),
        monto_a_vencimiento=Decimal("2200.00"),
        fecha_vencimiento=date(2026, 12, 31),
    )
    plazo_temprano = _plazo_fijo(
        plazo_id=2,
        monto_ingresado=Decimal("1000.00"),
        monto_a_vencimiento=Decimal("1100.00"),
        fecha_vencimiento=date(2026, 8, 15),
    )
    metadata = InformePlazoFijoMetadata(
        caja_nombre="Gabriel",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 12, 31),
        generated_at=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
    )
    resumen = PlazosFijosResumen(
        total_monto_ingresado_activos=Decimal("3000.00"),
        total_monto_a_vencimiento_activos=Decimal("3300.00"),
    )

    pdf_bytes = render_plazo_fijo_pdf(
        metadata=metadata,
        plazos=[plazo_temprano, plazo_tarde],
        resumen=resumen,
        compress=False,
    )
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")

    assert pdf_text.index("1000.00") < pdf_text.index("2000.00")


def test_render_plazo_fijo_pdf_empty_period_shows_message() -> None:
    metadata = InformePlazoFijoMetadata(
        caja_nombre="Gabriel",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        generated_at=datetime(2026, 1, 31, 12, 0, tzinfo=timezone.utc),
    )
    resumen = PlazosFijosResumen(
        total_monto_ingresado_activos=Decimal("0"),
        total_monto_a_vencimiento_activos=Decimal("0"),
    )

    pdf_bytes = render_plazo_fijo_pdf(
        metadata=metadata,
        plazos=[],
        resumen=resumen,
        compress=False,
    )
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")

    assert "No hay plazos fijos en el periodo seleccionado." in pdf_text
    assert "Monto ingresado" not in pdf_text


def test_render_caja_pdf_shows_resolved_period_in_header() -> None:
    metadata = InformeCajaMetadata(
        caja_nombre="Ebel",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 7, 17),
        generated_at=datetime(2026, 7, 17, 10, 0, tzinfo=timezone.utc),
    )

    pdf_bytes = render_caja_pdf(
        metadata=metadata,
        movimientos=[],
        saldo_cierre=None,
        saldo_actual=Decimal("0"),
        compress=False,
    )
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")

    assert "Periodo: 01/04/2026 - 17/07/2026" in pdf_text


def test_render_caja_pdf_uses_times_font() -> None:
    metadata = InformeCajaMetadata(
        caja_nombre="Ebel",
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 31),
        generated_at=datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc),
    )

    pdf_bytes = render_caja_pdf(
        metadata=metadata,
        movimientos=[],
        saldo_cierre=None,
        saldo_actual=Decimal("0"),
        compress=False,
    )

    assert b"/BaseFont /Times" in pdf_bytes


def test_render_caja_pdf_multipage_repeats_table_header() -> None:
    movimientos = [
        _movimiento(
            descripcion=f"Movimiento {index}",
            monto=Decimal("10.00"),
            tipo="entrada",
            subtotal=Decimal(f"{index * 10}.00"),
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
            movimiento_id=index,
        )
        for index in range(1, 31)
    ]
    metadata = InformeCajaMetadata(
        caja_nombre="Ebel",
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 31),
        generated_at=datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc),
    )

    pdf_bytes = render_caja_pdf(
        metadata=metadata,
        movimientos=movimientos,
        saldo_cierre=Decimal("300.00"),
        saldo_actual=Decimal("300.00"),
        compress=False,
    )
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")

    assert pdf_bytes.count(b"/Type /Page") >= 2
    assert pdf_text.count("Descripcion") >= 2
    assert "Movimiento 1" in pdf_text
    assert "Movimiento 30" in pdf_text
