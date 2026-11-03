from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.movimiento import Movimiento
from app.models.plazo_fijo import PlazoFijo
from app.services.saldo_futuro import FilaSaldoFuturo
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
        saldo_cierre_ars=Decimal("1500.00"),
        saldo_cierre_usd=None,
        saldo_actual_ars=Decimal("2000.00"),
        saldo_actual_usd=Decimal("0"),
        compress=False,
    )

    assert pdf_bytes.startswith(b"%PDF")
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
    assert "Informe de Caja" in pdf_text
    assert "Ebel" in pdf_text
    assert "Entrada +1500.00" in pdf_text
    assert "Saldo ARS al cierre del per" in pdf_text
    assert "1500.00" in pdf_text
    assert "Saldo actual ARS" in pdf_text
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
        saldo_cierre_ars=Decimal("500.00"),
        saldo_cierre_usd=None,
        saldo_actual_ars=Decimal("500.00"),
        saldo_actual_usd=Decimal("0"),
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
        saldo_cierre_ars=None,
        saldo_cierre_usd=None,
        saldo_actual_ars=Decimal("750.00"),
        saldo_actual_usd=Decimal("0"),
        compress=False,
    )
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")

    assert "No hay movimientos en el per" in pdf_text
    assert "Saldo ARS al cierre del per" not in pdf_text
    assert "Saldo actual ARS" in pdf_text
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
        saldo_cierre_ars=None,
        saldo_cierre_usd=None,
        saldo_actual_ars=Decimal("0"),
        saldo_actual_usd=Decimal("0"),
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
        saldo_cierre_ars=None,
        saldo_cierre_usd=None,
        saldo_actual_ars=Decimal("0"),
        saldo_actual_usd=Decimal("0"),
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
        saldo_cierre_ars=Decimal("300.00"),
        saldo_cierre_usd=None,
        saldo_actual_ars=Decimal("300.00"),
        saldo_actual_usd=Decimal("0"),
        compress=False,
    )
    pdf_text = pdf_bytes.decode("latin-1", errors="ignore")

    assert pdf_bytes.count(b"/Type /Page") >= 2
    assert pdf_text.count("Descripcion") >= 2
    assert "Movimiento 1" in pdf_text
    assert "Movimiento 30" in pdf_text


# ---------------------------------------------------------------------------
# T074 — feature 010 (US6): cheques en el informe de Caja
# ---------------------------------------------------------------------------

METADATA = InformeCajaMetadata(
    caja_nombre="Ebel",
    date_from=date(2026, 3, 1),
    date_to=date(2026, 3, 31),
    generated_at=datetime(2026, 3, 31, 18, 0, tzinfo=timezone.utc),
)


def _cheque(
    *,
    cheque_id: int = 50,
    instrumento: str = "cheque",
    tipo: str = "entrada",
    monto: str = "500.00",
    moneda: str = "ARS",
    descripcion: str = "Cheque cliente",
    fecha_liquidacion: date = date(2026, 11, 5),
    liquidado_at: datetime | None = None,
    subtotal: str | None = None,
) -> Movimiento:
    cheque = Movimiento(
        caja_id=2,
        descripcion=descripcion,
        monto=Decimal(monto),
        tipo=tipo,
        moneda=moneda,
        instrumento=instrumento,
        fecha_liquidacion=fecha_liquidacion,
        fecha_liquidado=liquidado_at,
        subtotal=Decimal(subtotal) if subtotal is not None else None,
        created_by=1,
    )
    cheque.id = cheque_id
    cheque.created_at = datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc)
    return cheque


def _render(**overrides) -> str:
    kwargs = dict(
        metadata=METADATA,
        movimientos=[],
        saldo_cierre_ars=None,
        saldo_cierre_usd=None,
        saldo_actual_ars=Decimal("1000.00"),
        saldo_actual_usd=Decimal("0"),
        compress=False,
    )
    kwargs.update(overrides)
    pdf_bytes = render_caja_pdf(**kwargs)
    assert pdf_bytes.startswith(b"%PDF")
    return pdf_bytes.decode("latin-1", errors="ignore")


def test_liquidated_cheque_is_marked_in_the_movements_table_with_its_effective_date() -> None:
    liquidado = _cheque(
        instrumento="echeque",
        descripcion="Pago proveedor",
        liquidado_at=datetime(2026, 3, 20, 15, 0, tzinfo=timezone.utc),
        subtotal="500.00",
    )
    comun = _movimiento(
        descripcion="Cobro comun",
        monto=Decimal("10.00"),
        tipo="entrada",
        subtotal=Decimal("10.00"),
        created_at=datetime(2026, 3, 10, 14, 30, tzinfo=timezone.utc),
        movimiento_id=3,
    )

    text = _render(movimientos=[liquidado, comun], saldo_cierre_ars=Decimal("500.00"))

    assert "[Echeque] Pago proveedor" in text
    assert "20/03/2026" in text  # effective date (liquidation), not the creation date
    assert "Cobro comun" in text
    assert "[Cheque] Cobro comun" not in text


def test_cheques_pendientes_section_lists_pending_cheques() -> None:
    pendiente = _cheque(descripcion="Cheque pendiente uno", fecha_liquidacion=date(2026, 11, 5))
    salida = _cheque(
        cheque_id=51,
        instrumento="echeque",
        tipo="salida",
        monto="200.00",
        moneda="USD",
        descripcion="Echeque pendiente dos",
        fecha_liquidacion=date(2026, 11, 20),
    )

    text = _render(cheques_pendientes=[pendiente, salida], cheques_pendientes_total=2)

    assert "Cheques pendientes" in text
    assert "[Cheque] Cheque pendiente uno" in text
    assert "[Echeque] Echeque pendiente dos" in text
    assert "Entrada +500.00 ARS" in text
    assert "Salida -200.00 USD" in text
    assert "05/11/2026" in text
    assert "20/11/2026" in text
    assert "05/03/2026" in text  # fecha de carga


def test_cheques_pendientes_section_without_rows_shows_message() -> None:
    text = _render(cheques_pendientes=[], cheques_pendientes_total=0)

    assert "Cheques pendientes" in text
    assert "No hay cheques pendientes" in text


def test_cheques_pendientes_cap_note_when_truncated() -> None:
    text = _render(cheques_pendientes=[_cheque()], cheques_pendientes_total=1500)

    assert "1500" in text
    assert "primeros" in text


def test_saldo_a_futuro_section_per_moneda_with_vencido_mark() -> None:
    futuro = {
        "ARS": (
            Decimal("1000.00"),
            [
                FilaSaldoFuturo(date(2026, 3, 1), True, 1, Decimal("100.00"), Decimal("1100.00")),
                FilaSaldoFuturo(date(2026, 11, 5), False, 2, Decimal("400.00"), Decimal("1500.00")),
                FilaSaldoFuturo(date(2026, 11, 20), False, 1, Decimal("-200.00"), Decimal("1300.00")),
            ],
        ),
        "USD": (Decimal("50.00"), []),
    }

    text = _render(saldo_futuro=futuro)

    assert "Saldo a futuro" in text
    assert "Saldo a futuro ARS" in text
    assert "Saldo a futuro USD" in text
    assert "Hoy" in text
    for expected in ("1000.00", "1100.00", "1500.00", "1300.00", "-200.00", "05/11/2026"):
        assert expected in text
    assert "vencido" in text.lower()
    assert "50.00" in text


def test_saldo_a_futuro_is_not_filtered_by_period_note() -> None:
    text = _render(saldo_futuro={"ARS": (Decimal("1.00"), []), "USD": (Decimal("0"), [])})

    assert "no filtrado por periodo" in text


def test_sections_are_omitted_when_not_provided() -> None:
    text = _render()

    assert "Cheques pendientes" not in text
    assert "Saldo a futuro" not in text


def test_new_sections_render_with_latin1_safe_text() -> None:
    pendiente = _cheque(descripcion="Cheque ñandú á é í ó ú")

    # Must not raise (core font is latin-1 only) and must keep producing a valid PDF.
    text = _render(
        cheques_pendientes=[pendiente],
        cheques_pendientes_total=1,
        saldo_futuro={"ARS": (Decimal("0"), []), "USD": (Decimal("0"), [])},
    )

    assert text.startswith("%PDF")


def test_render_plazo_fijo_pdf_is_unchanged_by_cheques() -> None:
    plazo = _plazo_fijo(
        plazo_id=1,
        monto_ingresado=Decimal("1000.00"),
        monto_a_vencimiento=Decimal("1100.00"),
        fecha_vencimiento=date(2026, 12, 31),
    )
    resumen = PlazosFijosResumen(
        total_monto_ingresado_activos=Decimal("1000.00"),
        total_monto_a_vencimiento_activos=Decimal("1100.00"),
    )

    text = render_plazo_fijo_pdf(
        metadata=InformePlazoFijoMetadata(
            caja_nombre="Gabriel",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
            generated_at=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
        ),
        plazos=[plazo],
        resumen=resumen,
        compress=False,
    ).decode("latin-1", errors="ignore")

    assert "Informe de Plazos Fijos" in text
    assert "Cheques pendientes" not in text
    assert "Saldo a futuro" not in text


def test_saldo_a_futuro_lists_the_description_of_each_cheque() -> None:
    from app.services.saldo_futuro import DetalleCheque

    futuro = {
        "ARS": (
            Decimal("1000.00"),
            [
                FilaSaldoFuturo(
                    date(2026, 11, 5),
                    False,
                    2,
                    Decimal("200.00"),
                    Decimal("1200.00"),
                    detalle=(
                        DetalleCheque("Honorarios Perez", "cheque", "entrada", Decimal("300.00")),
                        DetalleCheque("Pago sellado", "echeque", "salida", Decimal("100.00")),
                    ),
                )
            ],
        ),
        "USD": (Decimal("0"), []),
    }

    text = _render(saldo_futuro=futuro)

    assert "Honorarios Perez" in text
    assert "Pago sellado" in text
    assert "Echeque" in text
    assert "+300.00" in text and "-100.00" in text
