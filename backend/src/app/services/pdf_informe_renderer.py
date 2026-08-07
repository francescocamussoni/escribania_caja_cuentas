from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import TypeVar

from fpdf import FPDF

from app.core.dates import ARGENTINA_TZ
from app.models.movimiento import Movimiento
from app.models.plazo_fijo import PlazoFijo
from app.schemas.movimiento import format_decimal
from app.services.plazo_fijo_service import PlazosFijosResumen

FONT_FAMILY = "Times"
TITLE_SIZE = 14
META_SIZE = 11
BODY_SIZE = 10
TABLE_HEADER_SIZE = 10
TABLE_BODY_SIZE = 9
ROW_HEIGHT = 8
MARGIN_LEFT = 20
MARGIN_TOP = 20
MARGIN_RIGHT = 20
MARGIN_BOTTOM = 20

T = TypeVar("T")


@dataclass(frozen=True)
class InformeCajaMetadata:
    caja_nombre: str
    date_from: date
    date_to: date
    generated_at: datetime


InformePlazoFijoMetadata = InformeCajaMetadata


def _format_ar_datetime(value: datetime) -> str:
    localized = value
    if value.tzinfo is None:
        localized = value.replace(tzinfo=ARGENTINA_TZ)
    else:
        localized = value.astimezone(ARGENTINA_TZ)
    return localized.strftime("%d/%m/%Y %H:%M")


def _format_period(date_from: date, date_to: date) -> str:
    return f"{date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')}"


def _format_monto_movimiento(movimiento: Movimiento) -> str:
    amount = format_decimal(movimiento.monto)
    if movimiento.tipo == "entrada":
        return f"Entrada +{amount}"
    return f"Salida -{amount}"


def _format_ar_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


class InformePdf(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font(FONT_FAMILY, "", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align="C")


def _create_pdf(*, compress: bool) -> InformePdf:
    pdf = InformePdf(orientation="P", unit="mm", format="A4")
    pdf.set_compression(compress)
    pdf.set_margins(MARGIN_LEFT, MARGIN_TOP, MARGIN_RIGHT)
    pdf.set_auto_page_break(auto=True, margin=MARGIN_BOTTOM)
    pdf.alias_nb_pages()
    return pdf


def _write_informe_header(
    pdf: InformePdf,
    *,
    title: str,
    caja_nombre: str,
    date_from: date,
    date_to: date,
    generated_at: datetime,
) -> None:
    pdf.set_font(FONT_FAMILY, "B", TITLE_SIZE)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT_FAMILY, "", META_SIZE)
    pdf.cell(0, 7, f"Caja: {caja_nombre}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0,
        7,
        f"Periodo: {_format_period(date_from, date_to)}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        7,
        f"Generado: {_format_ar_datetime(generated_at)}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)


def _write_table(
    pdf: InformePdf,
    *,
    headers: Sequence[str],
    col_widths: Sequence[float],
    rows: Sequence[T],
    render_row: Callable[[InformePdf, T, Sequence[float]], None],
) -> None:
    def write_header() -> None:
        pdf.set_font(FONT_FAMILY, "B", TABLE_HEADER_SIZE)
        for header, width in zip(headers, col_widths, strict=False):
            pdf.cell(width, ROW_HEIGHT, header, border=1)
        pdf.ln()

    write_header()
    pdf.set_font(FONT_FAMILY, "", TABLE_BODY_SIZE)
    for row in rows:
        if pdf.get_y() + ROW_HEIGHT > pdf.page_break_trigger:
            pdf.add_page()
            write_header()
            pdf.set_font(FONT_FAMILY, "", TABLE_BODY_SIZE)
        render_row(pdf, row, col_widths)
        pdf.ln()


def _render_movimiento_row(
    pdf: InformePdf,
    movimiento: Movimiento,
    col_widths: Sequence[float],
) -> None:
    pdf.cell(col_widths[0], ROW_HEIGHT, movimiento.descripcion[:60], border=1)
    pdf.cell(col_widths[1], ROW_HEIGHT, _format_monto_movimiento(movimiento), border=1)
    pdf.cell(col_widths[2], ROW_HEIGHT, format_decimal(movimiento.subtotal), border=1)
    pdf.cell(
        col_widths[3],
        ROW_HEIGHT,
        _format_ar_datetime(movimiento.created_at),
        border=1,
    )


def _render_plazo_row(
    pdf: InformePdf,
    plazo: PlazoFijo,
    col_widths: Sequence[float],
) -> None:
    pdf.cell(col_widths[0], ROW_HEIGHT, format_decimal(plazo.monto_ingresado), border=1)
    pdf.cell(col_widths[1], ROW_HEIGHT, _format_ar_date(plazo.fecha_vencimiento), border=1)
    pdf.cell(col_widths[2], ROW_HEIGHT, format_decimal(plazo.monto_a_vencimiento), border=1)


def render_caja_pdf(
    *,
    metadata: InformeCajaMetadata,
    movimientos: list[Movimiento],
    saldo_cierre: Decimal | None,
    saldo_actual: Decimal,
    compress: bool = True,
) -> bytes:
    pdf = _create_pdf(compress=compress)
    pdf.add_page()
    _write_informe_header(
        pdf,
        title="Informe de Caja",
        caja_nombre=metadata.caja_nombre,
        date_from=metadata.date_from,
        date_to=metadata.date_to,
        generated_at=metadata.generated_at,
    )

    if not movimientos:
        pdf.set_font(FONT_FAMILY, "I", BODY_SIZE)
        pdf.multi_cell(
            0,
            7,
            "No hay movimientos en el periodo seleccionado.",
        )
    else:
        _write_table(
            pdf,
            headers=("Descripcion", "Monto", "Subtotal", "Fecha"),
            col_widths=(70, 40, 35, 40),
            rows=movimientos,
            render_row=_render_movimiento_row,
        )

    pdf.ln(6)
    pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
    if saldo_cierre is not None:
        pdf.cell(
            0,
            8,
            f"Saldo al cierre del periodo: $ {format_decimal(saldo_cierre)}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.cell(
        0,
        8,
        f"Saldo actual: $ {format_decimal(saldo_actual)}",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


def render_plazo_fijo_pdf(
    *,
    metadata: InformePlazoFijoMetadata,
    plazos: list[PlazoFijo],
    resumen: PlazosFijosResumen,
    compress: bool = True,
) -> bytes:
    pdf = _create_pdf(compress=compress)
    pdf.add_page()
    _write_informe_header(
        pdf,
        title="Informe de Plazos Fijos",
        caja_nombre=metadata.caja_nombre,
        date_from=metadata.date_from,
        date_to=metadata.date_to,
        generated_at=metadata.generated_at,
    )

    pdf.set_font(FONT_FAMILY, "B", BODY_SIZE)
    pdf.cell(
        0,
        8,
        (
            "Dinero ingresado en plazos activos: "
            f"$ {format_decimal(resumen.total_monto_ingresado_activos)}"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        8,
        (
            "Dinero a cobrar al vencer: "
            f"$ {format_decimal(resumen.total_monto_a_vencimiento_activos)}"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    if not plazos:
        pdf.set_font(FONT_FAMILY, "I", BODY_SIZE)
        pdf.multi_cell(
            0,
            7,
            "No hay plazos fijos en el periodo seleccionado.",
        )
    else:
        _write_table(
            pdf,
            headers=("Monto ingresado", "Fecha vencimiento", "Monto a vencimiento"),
            col_widths=(55, 55, 55),
            rows=plazos,
            render_row=_render_plazo_row,
        )

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
