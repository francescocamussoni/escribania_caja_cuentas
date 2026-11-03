"""
T053 — TDD: `proyectar_saldo_futuro` (feature 010, US4).

Función pura: agrupa los cheques pendientes por fecha de liquidación y acumula el efecto
neto sobre el saldo actual. Se calcula por moneda de forma independiente (el llamador la
invoca una vez por moneda).
"""

from datetime import date
from decimal import Decimal

from app.services.saldo_futuro import ChequeProyectable, FilaSaldoFuturo, proyectar_saldo_futuro

HOY = date(2026, 10, 21)
D1 = date(2026, 11, 5)
D2 = date(2026, 11, 20)


def _cheque(tipo: str, monto: str, fecha: date) -> ChequeProyectable:
    return ChequeProyectable(tipo=tipo, monto=Decimal(monto), fecha_liquidacion=fecha)


def test_spec_example_is_cumulative() -> None:
    filas = proyectar_saldo_futuro(
        Decimal("1000.00"),
        [_cheque("entrada", "500.00", D1), _cheque("salida", "200.00", D2)],
        HOY,
    )

    assert [(f.fecha_liquidacion, f.efecto_neto, f.saldo_proyectado) for f in filas] == [
        (D1, Decimal("500.00"), Decimal("1500.00")),
        (D2, Decimal("-200.00"), Decimal("1300.00")),
    ]


def test_groups_cheques_with_the_same_date_in_one_row() -> None:
    filas = proyectar_saldo_futuro(
        Decimal("0.00"),
        [
            _cheque("entrada", "300.00", D1),
            _cheque("salida", "100.00", D1),
            _cheque("entrada", "50.00", D1),
        ],
        HOY,
    )

    assert len(filas) == 1
    assert filas[0] == FilaSaldoFuturo(
        fecha_liquidacion=D1,
        vencido=False,
        cheques=3,
        efecto_neto=Decimal("250.00"),
        saldo_proyectado=Decimal("250.00"),
        detalle=filas[0].detalle,
    )
    assert len(filas[0].detalle) == 3


def test_rows_are_ordered_by_date_ascending_regardless_of_input_order() -> None:
    filas = proyectar_saldo_futuro(
        Decimal("100.00"),
        [_cheque("entrada", "1.00", D2), _cheque("entrada", "1.00", D1)],
        HOY,
    )

    assert [f.fecha_liquidacion for f in filas] == [D1, D2]
    assert [f.saldo_proyectado for f in filas] == [Decimal("101.00"), Decimal("102.00")]


def test_vencido_is_fecha_less_than_or_equal_to_hoy() -> None:
    filas = proyectar_saldo_futuro(
        Decimal("0.00"),
        [
            _cheque("entrada", "1.00", date(2026, 10, 20)),
            _cheque("entrada", "1.00", HOY),
            _cheque("entrada", "1.00", date(2026, 10, 22)),
        ],
        HOY,
    )

    assert [f.vencido for f in filas] == [True, True, False]


def test_overdue_cheques_are_still_projected() -> None:
    filas = proyectar_saldo_futuro(
        Decimal("10.00"), [_cheque("salida", "4.00", date(2026, 1, 1))], HOY
    )

    assert filas[0].vencido is True
    assert filas[0].saldo_proyectado == Decimal("6.00")


def test_negative_projected_balance_is_allowed() -> None:
    filas = proyectar_saldo_futuro(
        Decimal("100.00"), [_cheque("salida", "250.00", D1)], HOY
    )

    assert filas[0].efecto_neto == Decimal("-250.00")
    assert filas[0].saldo_proyectado == Decimal("-150.00")


def test_empty_list_yields_no_rows() -> None:
    assert proyectar_saldo_futuro(Decimal("1000.00"), [], HOY) == []


def test_uses_decimal_arithmetic_without_float_drift() -> None:
    filas = proyectar_saldo_futuro(
        Decimal("0.00"),
        [_cheque("entrada", "0.10", D1), _cheque("entrada", "0.20", D2)],
        HOY,
    )

    assert filas[-1].saldo_proyectado == Decimal("0.30")


def test_currencies_are_independent_by_calling_once_per_moneda() -> None:
    ars = proyectar_saldo_futuro(Decimal("1000.00"), [_cheque("entrada", "500.00", D1)], HOY)
    usd = proyectar_saldo_futuro(Decimal("50.00"), [_cheque("salida", "20.00", D1)], HOY)

    assert ars[0].saldo_proyectado == Decimal("1500.00")
    assert usd[0].saldo_proyectado == Decimal("30.00")


def test_each_row_carries_the_description_of_its_cheques_in_input_order() -> None:
    filas = proyectar_saldo_futuro(
        Decimal("0.00"),
        [
            ChequeProyectable("entrada", Decimal("300.00"), D1, "Honorarios Pérez", "cheque"),
            ChequeProyectable("salida", Decimal("100.00"), D1, "Pago sellado", "echeque"),
            ChequeProyectable("entrada", Decimal("50.00"), D2, "Otro cobro", "cheque"),
        ],
        HOY,
    )

    assert [
        (d.descripcion, d.instrumento, d.tipo, d.monto) for d in filas[0].detalle
    ] == [
        ("Honorarios Pérez", "cheque", "entrada", Decimal("300.00")),
        ("Pago sellado", "echeque", "salida", Decimal("100.00")),
    ]
    assert [d.descripcion for d in filas[1].detalle] == ["Otro cobro"]


# ---------------------------------------------------------------------------
# saldo_a_fecha: Valor de caja total en una fecha elegida
# ---------------------------------------------------------------------------

from app.services.saldo_futuro import saldo_a_fecha  # noqa: E402


def _filas() -> list[FilaSaldoFuturo]:
    return proyectar_saldo_futuro(
        Decimal("1000.00"),
        [
            _cheque("entrada", "500.00", D1),
            _cheque("salida", "200.00", D2),
            _cheque("entrada", "50.00", date(2026, 10, 1)),  # vencido
        ],
        HOY,
    )


def test_saldo_a_fecha_before_any_due_date_includes_only_overdue() -> None:
    efecto, saldo, cheques = saldo_a_fecha(Decimal("1000.00"), _filas(), date(2026, 10, 25))

    assert (efecto, saldo, cheques) == (Decimal("50.00"), Decimal("1050.00"), 1)


def test_saldo_a_fecha_is_inclusive_and_cumulative() -> None:
    assert saldo_a_fecha(Decimal("1000.00"), _filas(), D1) == (
        Decimal("550.00"), Decimal("1550.00"), 2,
    )
    assert saldo_a_fecha(Decimal("1000.00"), _filas(), D2) == (
        Decimal("350.00"), Decimal("1350.00"), 3,
    )


def test_saldo_a_fecha_without_cheques_equals_saldo_actual() -> None:
    assert saldo_a_fecha(Decimal("77.00"), [], D2) == (Decimal("0"), Decimal("77.00"), 0)
