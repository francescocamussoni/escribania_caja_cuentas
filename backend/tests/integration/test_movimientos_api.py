from decimal import Decimal

import pytest
from httpx import AsyncClient
from uuid import uuid4


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
async def test_post_movimiento_returns_201_with_contract_shape(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    caja_id = 2
    saldo_before = await client.get(
        f"/api/v1/cajas/{caja_id}/saldo",
        headers=secretaria_headers,
    )
    assert saldo_before.status_code == 200
    previous_subtotal = saldo_before.json()["saldo_actual"]

    payload = {
        "descripcion": "Pago cliente",
        "monto": "5000.00",
        "tipo": "entrada",
    }
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json=payload,
        headers=secretaria_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["descripcion"] == payload["descripcion"]
    assert body["monto"] == payload["monto"]
    assert body["tipo"] == payload["tipo"]
    assert body["subtotal"] == str(Decimal(previous_subtotal) + Decimal("5000.00"))
    assert body["id"]
    assert body["fecha"]
    assert "editable" in body
    assert body["caja"]["id"] == caja_id
    assert body["caja"]["nombre"]


@pytest.mark.asyncio
async def test_get_movimientos_returns_paginated_newest_first(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    suffix = uuid4().hex[:8]
    caja_id = 2
    for index in range(3):
        await client.post(
            f"/api/v1/cajas/{caja_id}/movimientos",
            json={
                "descripcion": f"Movimiento {suffix} {index}",
                "monto": "100.00",
                "tipo": "entrada",
            },
            headers=secretaria_headers,
        )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_items"] >= 3
    assert body["total_pages"] >= 1
    created = [item for item in body["items"] if suffix in item["descripcion"]]
    assert len(created) == 3
    assert created[0]["descripcion"] == f"Movimiento {suffix} 2"
    assert created[1]["descripcion"] == f"Movimiento {suffix} 1"
    assert created[2]["descripcion"] == f"Movimiento {suffix} 0"


@pytest.mark.asyncio
async def test_escribano_post_movimiento_returns_403(
    client: AsyncClient,
    escribano_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/cajas/1/movimientos",
        json={
            "descripcion": "Intento no autorizado",
            "monto": "100.00",
            "tipo": "entrada",
        },
        headers=escribano_headers,
    )

    assert response.status_code == 403
    body = response.json()
    assert body["detail"]
