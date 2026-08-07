import re
from datetime import date

from app.schemas.informe import InformeModo, InformeTipo

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00]+')


def normalize_caja_name(nombre: str) -> str:
    normalized = nombre.strip().replace(" ", "-")
    return _INVALID_FILENAME_CHARS.sub("", normalized)


def build_informe_filename(
    *,
    tipo: InformeTipo,
    caja_nombre: str,
    modo: InformeModo,
    hasta_hoy: bool,
    mes: int | None,
    anio: int | None,
    date_from: date,
    date_to: date,
) -> str:
    tipo_part = tipo.value
    name_part = normalize_caja_name(caja_nombre)

    if modo == InformeModo.MES_ANIO and not hasta_hoy:
        if mes is None or anio is None:
            raise ValueError("mes y anio son obligatorios para el nombre de archivo")
        period = f"{anio:04d}-{mes:02d}"
    else:
        period = f"{date_from:%Y-%m-%d}_{date_to:%Y-%m-%d}"

    return f"{tipo_part}-{name_part}-{period}.pdf"
