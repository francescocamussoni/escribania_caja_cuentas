import pytest
from httpx import AsyncClient
from unittest.mock import patch

from app.services.informe_service import InformeService


@pytest.fixture
async def secretaria_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def escribano_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "escribano", "password": "escribano"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_post_informe_caja_returns_pdf_bytes(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/informes/pdf",
        json={
            "tipo": "CAJA",
            "caja_id": 2,
            "modo": "MES_ANIO",
            "mes": 1,
            "anio": 2026,
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "CAJA-Ebel" in response.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_post_informe_rejects_invalid_date_range(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/informes/pdf",
        json={
            "tipo": "CAJA",
            "caja_id": 1,
            "modo": "PERIODO",
            "fecha_inicio": "2026-06-01",
            "fecha_fin": "2026-01-01",
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_informe_without_auth_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/informes/pdf",
        json={
            "tipo": "CAJA",
            "caja_id": 1,
            "modo": "MES_ANIO",
            "mes": 1,
            "anio": 2026,
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
@patch.object(InformeService, "get_caja", return_value=None)
async def test_post_informe_unknown_caja_returns_404(
    _mock_get_caja: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/informes/pdf",
        json={
            "tipo": "CAJA",
            "caja_id": 2,
            "modo": "MES_ANIO",
            "mes": 1,
            "anio": 2026,
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_informe_escribano_allowed(
    client: AsyncClient,
    escribano_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/informes/pdf",
        json={
            "tipo": "CAJA",
            "caja_id": 1,
            "modo": "MES_ANIO",
            "mes": 1,
            "anio": 2026,
        },
        headers=escribano_headers,
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_post_informe_plazo_fijo_returns_pdf_bytes(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    caja_id = 5
    await client.post(
        f"/api/v1/cajas/{caja_id}/plazos-fijos",
        json={
            "monto_ingresado": "50000.00",
            "monto_a_vencimiento": "52500.00",
            "fecha_vencimiento": "2026-12-31",
        },
        headers=secretaria_headers,
    )

    response = await client.post(
        "/api/v1/informes/pdf",
        json={
            "tipo": "PLAZO_FIJO",
            "caja_id": caja_id,
            "modo": "PERIODO",
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-12-31",
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert "PLAZO_FIJO-Gabriel" in response.headers.get("content-disposition", "")


# ---------------------------------------------------------------------------
# T075 — feature 010 (US6): informe de Caja con cheques pendientes y saldo a futuro
# ---------------------------------------------------------------------------

from datetime import date, datetime, timezone  # noqa: E402

from app.core.dates import today_ar  # noqa: E402
from app.services import pdf_informe_renderer  # noqa: E402

from .cheque_helpers import insert_cheque  # noqa: E402

PDF_URL = "/api/v1/informes/pdf"

# These tests use the last seeded caja and wipe its movements before and after each test.
INFORME_CAJA_ID = 15


def _wipe_caja(caja_id: int) -> None:
    from sqlalchemy import delete

    from app.db.session import SessionLocal
    from app.models.movimiento import Movimiento

    with SessionLocal() as session:
        session.execute(delete(Movimiento).where(Movimiento.caja_id == caja_id))
        session.commit()


@pytest.fixture
def informe_caja() -> int:
    _wipe_caja(INFORME_CAJA_ID)
    yield INFORME_CAJA_ID
    _wipe_caja(INFORME_CAJA_ID)


@pytest.fixture
def pdf_text(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture the text of every CAJA PDF (rendered uncompressed so it is extractable)."""
    captured: list[str] = []
    real = pdf_informe_renderer.render_caja_pdf

    def wrapper(**kwargs):
        kwargs["compress"] = False
        pdf = real(**kwargs)
        captured.append(pdf.decode("latin-1", errors="ignore"))
        return pdf

    monkeypatch.setattr("app.api.routes.informes.render_caja_pdf", wrapper)
    return captured


def _caja_body(caja_id: int, **overrides) -> dict:
    today = today_ar()
    body = {
        "tipo": "CAJA",
        "caja_id": caja_id,
        "modo": "MES_ANIO",
        "mes": today.month,
        "anio": today.year,
    }
    body.update(overrides)
    return body


async def _common(client: AsyncClient, headers: dict, caja_id: int, tipo: str, monto: str, desc: str):
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": desc, "monto": monto, "tipo": tipo},
        headers=headers,
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["secretaria", "escribano"])
async def test_caja_informe_includes_cheques_pendientes_and_saldo_a_futuro_for_both_roles(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
    informe_caja: int,
    pdf_text: list[str],
    role: str,
) -> None:
    caja_id = informe_caja
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00", "Ingreso inicial")
    insert_cheque(
        caja_id,
        tipo="entrada",
        monto="500.00",
        fecha_liquidacion=date(2099, 11, 5),
        descripcion="Cheque D1 pendiente",
    )
    headers = secretaria_headers if role == "secretaria" else escribano_headers

    response = await client.post(PDF_URL, json=_caja_body(caja_id), headers=headers)

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    text = pdf_text[-1]
    assert "Cheques pendientes" in text
    assert "[Cheque] Cheque D1 pendiente" in text
    assert "Saldo a futuro ARS" in text
    assert "1000.00" in text and "1500.00" in text  # Hoy / D1
    assert "05/11/2099" in text


@pytest.mark.asyncio
async def test_pending_cheques_do_not_affect_listing_or_saldos(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    informe_caja: int,
    pdf_text: list[str],
) -> None:
    caja_id = informe_caja
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00", "Ingreso inicial")
    insert_cheque(caja_id, monto="777.00", descripcion="PENDIENTE-NO-LISTAR")

    response = await client.post(PDF_URL, json=_caja_body(caja_id), headers=secretaria_headers)

    assert response.status_code == 200
    text = pdf_text[-1]
    listing, _, pendientes = text.partition("Cheques pendientes")
    assert "PENDIENTE-NO-LISTAR" not in listing
    assert "PENDIENTE-NO-LISTAR" in pendientes
    assert "Ingreso inicial" in listing
    assert "Saldo ARS al cierre del periodo: $ 1000.00" in text
    assert "Saldo actual ARS: $ 1000.00" in text


@pytest.mark.asyncio
async def test_liquidated_cheque_is_listed_marked_and_counts_in_the_saldo(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    informe_caja: int,
    pdf_text: list[str],
) -> None:
    caja_id = informe_caja
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00", "Ingreso inicial")
    insert_cheque(
        caja_id,
        tipo="entrada",
        monto="250.00",
        fecha_liquidacion=date(2026, 1, 1),
        fecha_liquidado=datetime.now(timezone.utc),
        subtotal="1250.00",
        descripcion="Cheque ya cobrado",
        instrumento="echeque",
    )

    await client.post(PDF_URL, json=_caja_body(caja_id), headers=secretaria_headers)

    text = pdf_text[-1]
    assert "[Echeque] Cheque ya cobrado" in text
    assert "Saldo actual ARS: $ 1250.00" in text


@pytest.mark.asyncio
async def test_past_period_still_shows_current_pendings_projection_and_timestamp(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    informe_caja: int,
    pdf_text: list[str],
) -> None:
    caja_id = informe_caja
    insert_cheque(
        caja_id,
        tipo="salida",
        monto="30.00",
        fecha_liquidacion=date(2099, 12, 31),
        descripcion="Cheque futuro lejano",
    )

    response = await client.post(
        PDF_URL,
        json=_caja_body(caja_id, modo="PERIODO", fecha_inicio="2020-01-01", fecha_fin="2020-01-31", mes=None, anio=None),
        headers=secretaria_headers,
    )

    assert response.status_code == 200, response.text
    text = pdf_text[-1]
    assert "No hay movimientos en el per" in text
    assert "Cheque futuro lejano" in text
    assert "Saldo a futuro ARS" in text
    assert "-30.00" in text
    assert "Generado:" in text
    assert "no filtrado por periodo" in text


@pytest.mark.asyncio
async def test_saldo_a_futuro_in_the_pdf_matches_the_api(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    informe_caja: int,
    pdf_text: list[str],
) -> None:
    caja_id = informe_caja
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00", "Ingreso inicial")
    insert_cheque(caja_id, tipo="entrada", monto="500.00", fecha_liquidacion=date(2099, 11, 5))
    insert_cheque(caja_id, tipo="salida", monto="200.00", fecha_liquidacion=date(2099, 11, 20))
    api = (
        await client.get(f"/api/v1/cajas/{caja_id}/saldo-futuro", headers=secretaria_headers)
    ).json()

    await client.post(PDF_URL, json=_caja_body(caja_id), headers=secretaria_headers)

    text = pdf_text[-1]
    ars = next(m for m in api["monedas"] if m["moneda"] == "ARS")
    assert ars["saldo_actual"] == "1000.00"
    for fila in ars["filas"]:
        assert fila["saldo_proyectado"] in text
        assert fila["efecto_neto"] in text


@pytest.mark.asyncio
async def test_plazo_fijo_informe_is_unchanged(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    informe_caja: int,
    pdf_text: list[str],
) -> None:
    insert_cheque(informe_caja, descripcion="no debe aparecer en plazos")

    response = await client.post(
        PDF_URL,
        json={
            "tipo": "PLAZO_FIJO",
            "caja_id": informe_caja,
            "modo": "PERIODO",
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-12-31",
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert pdf_text == []  # the CAJA renderer was not used


@pytest.mark.asyncio
async def test_informe_pdf_works_for_cajas_created_from_configuracion(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    """Regresión: una caja agregada en Configuración (id > 15) también se puede imprimir."""
    caja_id = fresh_caja["id"]

    response = await client.post(PDF_URL, json=_caja_body(caja_id), headers=secretaria_headers)

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
