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
