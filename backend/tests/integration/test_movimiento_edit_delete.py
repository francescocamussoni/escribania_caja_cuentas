from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.movimiento import Movimiento


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


async def _create_movimiento(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    descripcion: str,
    monto: str,
    tipo: str,
    caja_id: int = 1,
) -> dict:
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": descripcion, "monto": monto, "tipo": tipo},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def _list_movimientos(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    caja_id: int = 1,
) -> list[dict]:
    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["items"]


async def _get_movimiento_by_id(
    client: AsyncClient,
    headers: dict[str, str],
    movimiento_id: int,
    *,
    caja_id: int = 1,
) -> dict:
    page = 1
    while True:
        response = await client.get(
            f"/api/v1/cajas/{caja_id}/movimientos?page={page}",
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        for item in body["items"]:
            if item["id"] == movimiento_id:
                return item
        if page >= body["total_pages"]:
            break
        page += 1
    raise AssertionError(f"Movimiento {movimiento_id} no encontrado")


def _set_movimiento_created_at(movimiento_id: int, created_at: datetime) -> None:
    with SessionLocal() as session:
        movimiento = session.scalar(
            select(Movimiento).where(Movimiento.id == movimiento_id)
        )
        assert movimiento is not None
        movimiento.created_at = created_at
        session.commit()


@pytest.mark.asyncio
async def test_patch_movimiento_recalculates_subsequent_subtotals(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    suffix = uuid4().hex[:8]
    caja_id = 2
    first = await _create_movimiento(
        client,
        secretaria_headers,
        descripcion=f"Entrada inicial {suffix}",
        monto="1000.00",
        tipo="entrada",
        caja_id=caja_id,
    )
    second = await _create_movimiento(
        client,
        secretaria_headers,
        descripcion=f"Segunda entrada {suffix}",
        monto="500.00",
        tipo="entrada",
        caja_id=caja_id,
    )
    third = await _create_movimiento(
        client,
        secretaria_headers,
        descripcion=f"Salida parcial {suffix}",
        monto="200.00",
        tipo="salida",
        caja_id=caja_id,
    )

    items_before = {
        item["id"]: item
        for item in [
            await _get_movimiento_by_id(
                client, secretaria_headers, first["id"], caja_id=caja_id
            ),
            await _get_movimiento_by_id(
                client, secretaria_headers, second["id"], caja_id=caja_id
            ),
            await _get_movimiento_by_id(
                client, secretaria_headers, third["id"], caja_id=caja_id
            ),
        ]
    }

    patch_response = await client.patch(
        f"/api/v1/cajas/{caja_id}/movimientos/{first['id']}",
        json={"monto": "2000.00"},
        headers=secretaria_headers,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["monto"] == "2000.00"

    before_second = items_before[second["id"]]
    before_third = items_before[third["id"]]
    after_second = await _get_movimiento_by_id(
        client, secretaria_headers, second["id"], caja_id=caja_id
    )
    after_third = await _get_movimiento_by_id(
        client, secretaria_headers, third["id"], caja_id=caja_id
    )

    delta = Decimal("1000.00")
    assert Decimal(after_second["subtotal"]) - Decimal(
        before_second["subtotal"]
    ) == delta
    assert Decimal(after_third["subtotal"]) - Decimal(before_third["subtotal"]) == delta


@pytest.mark.asyncio
async def test_delete_movimiento_recalculates_subsequent_subtotals(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    suffix = uuid4().hex[:8]
    caja_id = 2
    first = await _create_movimiento(
        client,
        secretaria_headers,
        descripcion=f"Entrada base {suffix}",
        monto="1000.00",
        tipo="entrada",
        caja_id=caja_id,
    )
    middle = await _create_movimiento(
        client,
        secretaria_headers,
        descripcion=f"Entrada a eliminar {suffix}",
        monto="500.00",
        tipo="entrada",
        caja_id=caja_id,
    )
    third = await _create_movimiento(
        client,
        secretaria_headers,
        descripcion=f"Salida final {suffix}",
        monto="200.00",
        tipo="salida",
        caja_id=caja_id,
    )

    items_before = {
        item["id"]: item
        for item in [
            await _get_movimiento_by_id(
                client, secretaria_headers, first["id"], caja_id=caja_id
            ),
            await _get_movimiento_by_id(
                client, secretaria_headers, middle["id"], caja_id=caja_id
            ),
            await _get_movimiento_by_id(
                client, secretaria_headers, third["id"], caja_id=caja_id
            ),
        ]
    }

    delete_response = await client.delete(
        f"/api/v1/cajas/{caja_id}/movimientos/{middle['id']}",
        headers=secretaria_headers,
    )
    assert delete_response.status_code == 204

    items_after = {
        item["id"]: item
        for item in [
            await _get_movimiento_by_id(
                client, secretaria_headers, first["id"], caja_id=caja_id
            ),
            await _get_movimiento_by_id(
                client, secretaria_headers, third["id"], caja_id=caja_id
            ),
        ]
    }
    assert middle["id"] not in items_after
    delta = Decimal("500.00")
    assert Decimal(items_after[first["id"]]["subtotal"]) == Decimal(
        items_before[first["id"]]["subtotal"]
    )
    assert Decimal(items_after[third["id"]]["subtotal"]) == Decimal(
        items_before[third["id"]]["subtotal"]
    ) - delta


@pytest.mark.asyncio
async def test_patch_movimiento_after_24h_returns_422(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    movimiento = await _create_movimiento(
        client,
        secretaria_headers,
        descripcion="Movimiento antiguo",
        monto="100.00",
        tipo="entrada",
    )
    _set_movimiento_created_at(
        movimiento["id"],
        datetime.now(timezone.utc) - timedelta(hours=25),
    )

    response = await client.patch(
        f"/api/v1/cajas/1/movimientos/{movimiento['id']}",
        json={"descripcion": "Intento tardío"},
        headers=secretaria_headers,
    )

    assert response.status_code == 422
    assert "24h" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_movimiento_after_24h_returns_422(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    movimiento = await _create_movimiento(
        client,
        secretaria_headers,
        descripcion="Movimiento antiguo delete",
        monto="100.00",
        tipo="entrada",
    )
    _set_movimiento_created_at(
        movimiento["id"],
        datetime.now(timezone.utc) - timedelta(hours=25),
    )

    response = await client.delete(
        f"/api/v1/cajas/1/movimientos/{movimiento['id']}",
        headers=secretaria_headers,
    )

    assert response.status_code == 422
    assert "24h" in response.json()["detail"]


@pytest.mark.asyncio
async def test_escribano_patch_movimiento_returns_403(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
) -> None:
    movimiento = await _create_movimiento(
        client,
        secretaria_headers,
        descripcion="Solo secretaria edita",
        monto="100.00",
        tipo="entrada",
    )

    response = await client.patch(
        f"/api/v1/cajas/1/movimientos/{movimiento['id']}",
        json={"descripcion": "Intento escribano"},
        headers=escribano_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_escribano_delete_movimiento_returns_403(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
) -> None:
    movimiento = await _create_movimiento(
        client,
        secretaria_headers,
        descripcion="Solo secretaria elimina",
        monto="100.00",
        tipo="entrada",
    )

    response = await client.delete(
        f"/api/v1/cajas/1/movimientos/{movimiento['id']}",
        headers=escribano_headers,
    )

    assert response.status_code == 403
