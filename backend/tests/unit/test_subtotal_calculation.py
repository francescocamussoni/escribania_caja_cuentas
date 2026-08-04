from decimal import Decimal

import pytest

from app.services.movimiento_service import compute_subtotal


@pytest.mark.parametrize(
    ("previous", "monto", "tipo", "expected"),
    [
        (Decimal("0"), Decimal("1000.00"), "entrada", Decimal("1000.00")),
        (Decimal("5000.00"), Decimal("2000.50"), "entrada", Decimal("7000.50")),
        (Decimal("5000.00"), Decimal("1500.00"), "salida", Decimal("3500.00")),
        (Decimal("100.00"), Decimal("250.00"), "salida", Decimal("-150.00")),
    ],
    ids=[
        "first-movimiento-entrada",
        "entrada-acumula",
        "salida-resta",
        "salida-subtotal-negativo",
    ],
)
def test_compute_subtotal(
    previous: Decimal,
    monto: Decimal,
    tipo: str,
    expected: Decimal,
) -> None:
    assert compute_subtotal(previous=previous, monto=monto, tipo=tipo) == expected


def test_compute_subtotal_rejects_invalid_tipo() -> None:
    with pytest.raises(ValueError, match="tipo"):
        compute_subtotal(
            previous=Decimal("0"),
            monto=Decimal("100"),
            tipo="invalido",
        )
