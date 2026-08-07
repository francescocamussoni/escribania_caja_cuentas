from datetime import date

import pytest

from app.schemas.informe import InformeModo, InformePdfRequest, InformeTipo
from app.services.informe_service import InformeDateRangeError, resolve_date_range

REFERENCE_TODAY = date(2026, 7, 17)


def test_mes_anio_single_month() -> None:
    request = InformePdfRequest(
        tipo=InformeTipo.CAJA,
        caja_id=2,
        modo=InformeModo.MES_ANIO,
        mes=3,
        anio=2026,
    )
    date_from, date_to = resolve_date_range(request, reference_today=REFERENCE_TODAY)
    assert date_from == date(2026, 3, 1)
    assert date_to == date(2026, 3, 31)


def test_mes_anio_hasta_hoy_abril_a_julio() -> None:
    request = InformePdfRequest(
        tipo=InformeTipo.CAJA,
        caja_id=2,
        modo=InformeModo.MES_ANIO,
        mes=4,
        anio=2026,
        hasta_hoy=True,
    )
    date_from, date_to = resolve_date_range(request, reference_today=REFERENCE_TODAY)
    assert date_from == date(2026, 4, 1)
    assert date_to == REFERENCE_TODAY


def test_periodo_explicit_range() -> None:
    request = InformePdfRequest(
        tipo=InformeTipo.CAJA,
        caja_id=2,
        modo=InformeModo.PERIODO,
        fecha_inicio=date(2026, 1, 15),
        fecha_fin=date(2026, 2, 28),
    )
    date_from, date_to = resolve_date_range(request, reference_today=REFERENCE_TODAY)
    assert date_from == date(2026, 1, 15)
    assert date_to == date(2026, 2, 28)


def test_periodo_hasta_hoy() -> None:
    request = InformePdfRequest(
        tipo=InformeTipo.PLAZO_FIJO,
        caja_id=5,
        modo=InformeModo.PERIODO,
        fecha_inicio=date(2026, 4, 1),
        hasta_hoy=True,
    )
    date_from, date_to = resolve_date_range(request, reference_today=REFERENCE_TODAY)
    assert date_from == date(2026, 4, 1)
    assert date_to == REFERENCE_TODAY


def test_mes_anio_hasta_hoy_start_after_today_raises() -> None:
    request = InformePdfRequest(
        tipo=InformeTipo.CAJA,
        caja_id=1,
        modo=InformeModo.MES_ANIO,
        mes=9,
        anio=2026,
        hasta_hoy=True,
    )
    with pytest.raises(InformeDateRangeError):
        resolve_date_range(request, reference_today=REFERENCE_TODAY)


def test_periodo_inicio_after_fin_rejected_at_schema() -> None:
    with pytest.raises(ValueError, match="fecha_inicio"):
        InformePdfRequest(
            tipo=InformeTipo.CAJA,
            caja_id=1,
            modo=InformeModo.PERIODO,
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 1, 1),
        )
