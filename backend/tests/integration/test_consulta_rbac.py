import pytest
from httpx import AsyncClient

from app.catalog.cajas import CAJAS_CATALOG


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
async def test_escribano_can_get_saldo_and_movimientos_for_all_cajas(
    client: AsyncClient,
    escribano_headers: dict[str, str],
    secretaria_headers: dict[str, str],
) -> None:
    await client.post(
        "/api/v1/cajas/1/movimientos",
        json={
            "descripcion": "Movimiento de prueba consulta",
            "monto": "250.00",
            "tipo": "entrada",
        },
        headers=secretaria_headers,
    )

    cajas_response = await client.get("/api/v1/cajas", headers=escribano_headers)
    assert cajas_response.status_code == 200
    cajas = cajas_response.json()
    # Integration tests share the DB within the session; other tests may add cajas,
    # so we assert at least the 15 catalog cajas are present.
    assert len(cajas) >= len(CAJAS_CATALOG)

    for caja in cajas:
        saldo_response = await client.get(
            f"/api/v1/cajas/{caja['id']}/saldo",
            headers=escribano_headers,
        )
        assert saldo_response.status_code == 200
        saldo_body = saldo_response.json()
        assert saldo_body["caja"]["id"] == caja["id"]
        assert "saldo_ars" in saldo_body

        movimientos_response = await client.get(
            f"/api/v1/cajas/{caja['id']}/movimientos?page=1",
            headers=escribano_headers,
        )
        assert movimientos_response.status_code == 200
        movimientos_body = movimientos_response.json()
        assert movimientos_body["page"] == 1
        assert movimientos_body["page_size"] == 20
        assert "items" in movimientos_body


@pytest.mark.asyncio
async def test_secretaria_can_get_saldo_and_movimientos_for_all_cajas(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    cajas_response = await client.get("/api/v1/cajas", headers=secretaria_headers)
    assert cajas_response.status_code == 200
    cajas = cajas_response.json()
    # Integration tests share the DB within the session; other tests may add cajas,
    # so we assert at least the 15 catalog cajas are present.
    assert len(cajas) >= len(CAJAS_CATALOG)

    for caja in cajas:
        saldo_response = await client.get(
            f"/api/v1/cajas/{caja['id']}/saldo",
            headers=secretaria_headers,
        )
        assert saldo_response.status_code == 200

        movimientos_response = await client.get(
            f"/api/v1/cajas/{caja['id']}/movimientos?page=1",
            headers=secretaria_headers,
        )
        assert movimientos_response.status_code == 200
