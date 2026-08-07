from datetime import date

import pytest

from app.core.filenames import build_informe_filename, normalize_caja_name
from app.schemas.informe import InformeModo, InformeTipo


def test_normalize_caja_name_replaces_spaces() -> None:
    assert normalize_caja_name("Maria Teresa") == "Maria-Teresa"
    assert normalize_caja_name("Ebel") == "Ebel"


def test_build_filename_mes_anio_only() -> None:
    filename = build_informe_filename(
        tipo=InformeTipo.CAJA,
        caja_nombre="Ebel",
        modo=InformeModo.MES_ANIO,
        hasta_hoy=False,
        mes=3,
        anio=2026,
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 31),
    )
    assert filename == "CAJA-Ebel-2026-03.pdf"


def test_build_filename_mes_anio_hasta_hoy() -> None:
    filename = build_informe_filename(
        tipo=InformeTipo.CAJA,
        caja_nombre="Ebel",
        modo=InformeModo.MES_ANIO,
        hasta_hoy=True,
        mes=4,
        anio=2026,
        date_from=date(2026, 4, 1),
        date_to=date(2026, 7, 17),
    )
    assert filename == "CAJA-Ebel-2026-04-01_2026-07-17.pdf"


def test_build_filename_periodo_range() -> None:
    filename = build_informe_filename(
        tipo=InformeTipo.PLAZO_FIJO,
        caja_nombre="Gabriel",
        modo=InformeModo.PERIODO,
        hasta_hoy=False,
        mes=None,
        anio=None,
        date_from=date(2026, 1, 15),
        date_to=date(2026, 2, 28),
    )
    assert filename == "PLAZO_FIJO-Gabriel-2026-01-15_2026-02-28.pdf"


def test_build_filename_mes_anio_requires_mes_anio_when_not_hasta_hoy() -> None:
    with pytest.raises(ValueError, match="mes y anio"):
        build_informe_filename(
            tipo=InformeTipo.CAJA,
            caja_nombre="Ebel",
            modo=InformeModo.MES_ANIO,
            hasta_hoy=False,
            mes=None,
            anio=None,
            date_from=date(2026, 3, 1),
            date_to=date(2026, 3, 31),
        )
