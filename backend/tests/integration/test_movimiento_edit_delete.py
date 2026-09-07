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
    moneda: str = "ARS",
) -> dict:
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": descripcion, "monto": monto, "tipo": tipo, "moneda": moneda},
        headers=headers,
    )
    assert response.status_code == 201
    # T012: response is now MovimientoCreateResponse {movimiento, complementario}
    return response.json()["movimiento"]


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
async def test_patch_movimiento_after_24h_is_allowed(
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
        json={"descripcion": "Edición tardía"},
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    assert response.json()["descripcion"] == "Edición tardía"


@pytest.mark.asyncio
async def test_delete_movimiento_after_24h_is_allowed(
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

    assert response.status_code == 204


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


# ---------------------------------------------------------------------------
# T014 — Recalculation scoped to currency stream on PATCH/DELETE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_moneda_recalculates_both_streams(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    PATCH that changes moneda from ARS to USD must:
    - Move the row into the USD stream (subtotal based on prior USD rows)
    - Recalculate the ARS stream (which now has one fewer row)
    """
    suffix = uuid4().hex[:8]
    caja_id = 8  # dedicated caja for this test

    # Capture existing ARS and USD saldos before this test adds its rows.
    saldo_resp = await client.get(
        f"/api/v1/cajas/{caja_id}/saldo",
        headers=secretaria_headers,
    )
    assert saldo_resp.status_code == 200
    prior_saldo_ars = Decimal(saldo_resp.json()["saldo_ars"])
    prior_saldo_usd = Decimal(saldo_resp.json()["saldo_usd"])

    # Build ARS stream: prior_ars + 1000, then + 500
    first_ars = await _create_movimiento(
        client, secretaria_headers,
        descripcion=f"ARS1 {suffix}", monto="1000.00", tipo="entrada",
        caja_id=caja_id, moneda="ARS",
    )
    second_ars = await _create_movimiento(
        client, secretaria_headers,
        descripcion=f"ARS2 {suffix}", monto="500.00", tipo="entrada",
        caja_id=caja_id, moneda="ARS",
    )
    # Build USD stream: prior_usd + 200
    first_usd = await _create_movimiento(
        client, secretaria_headers,
        descripcion=f"USD1 {suffix}", monto="200.00", tipo="entrada",
        caja_id=caja_id, moneda="USD",
    )

    assert Decimal(first_ars["subtotal"]) == prior_saldo_ars + Decimal("1000.00")
    assert Decimal(second_ars["subtotal"]) == prior_saldo_ars + Decimal("1500.00")
    assert Decimal(first_usd["subtotal"]) == prior_saldo_usd + Decimal("200.00")

    # PATCH second_ars: change moneda ARS→USD
    patch_resp = await client.patch(
        f"/api/v1/cajas/{caja_id}/movimientos/{second_ars['id']}",
        json={"moneda": "USD"},
        headers=secretaria_headers,
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["moneda"] == "USD"

    # ARS stream: second_ars removed → first_ars subtotal stays at prior_ars + 1000
    after_first_ars = await _get_movimiento_by_id(
        client, secretaria_headers, first_ars["id"], caja_id=caja_id
    )
    assert Decimal(after_first_ars["subtotal"]) == prior_saldo_ars + Decimal("1000.00"), (
        f"ARS stream should be recalculated. Got: {after_first_ars['subtotal']}"
    )

    # The moved row must now have moneda=USD
    patched_in_usd = await _get_movimiento_by_id(
        client, secretaria_headers, second_ars["id"], caja_id=caja_id
    )
    assert patched_in_usd["moneda"] == "USD"

    # Verify via saldo: moving a 500 entrada from ARS→USD adds 500 to saldo_usd
    # and removes 500 from saldo_ars (which only had first_ars=1000 left after the move).
    final_saldo_resp = await client.get(
        f"/api/v1/cajas/{caja_id}/saldo", headers=secretaria_headers
    )
    assert final_saldo_resp.status_code == 200
    final_saldo = final_saldo_resp.json()
    expected_final_ars = prior_saldo_ars + Decimal("1000.00")   # only first_ars remains
    expected_final_usd = prior_saldo_usd + Decimal("700.00")    # first_usd(200) + moved(500)
    assert Decimal(final_saldo["saldo_ars"]) == expected_final_ars, (
        f"saldo_ars after PATCH expected {expected_final_ars}, got {final_saldo['saldo_ars']}"
    )
    assert Decimal(final_saldo["saldo_usd"]) == expected_final_usd, (
        f"saldo_usd after PATCH expected {expected_final_usd}, got {final_saldo['saldo_usd']}"
    )


@pytest.mark.asyncio
async def test_patch_same_moneda_only_recalculates_one_stream(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """PATCH that does NOT change moneda must only touch the single stream."""
    suffix = uuid4().hex[:8]
    caja_id = 9

    # Capture prior saldos to compute expected values correctly
    prior_resp = await client.get(
        f"/api/v1/cajas/{caja_id}/saldo", headers=secretaria_headers
    )
    assert prior_resp.status_code == 200
    prior_saldo_ars = Decimal(prior_resp.json()["saldo_ars"])

    ars1 = await _create_movimiento(
        client, secretaria_headers,
        descripcion=f"ARS base {suffix}", monto="300.00", tipo="entrada",
        caja_id=caja_id, moneda="ARS",
    )
    ars2 = await _create_movimiento(
        client, secretaria_headers,
        descripcion=f"ARS second {suffix}", monto="100.00", tipo="entrada",
        caja_id=caja_id, moneda="ARS",
    )
    usd1 = await _create_movimiento(
        client, secretaria_headers,
        descripcion=f"USD only {suffix}", monto="50.00", tipo="entrada",
        caja_id=caja_id, moneda="USD",
    )

    # Patch ars1 monto: 300 → 600 (no moneda change)
    patch_resp = await client.patch(
        f"/api/v1/cajas/{caja_id}/movimientos/{ars1['id']}",
        json={"monto": "600.00"},
        headers=secretaria_headers,
    )
    assert patch_resp.status_code == 200

    # ARS stream recalculated: prior_ars + 600, then + 100 = prior_ars + 700
    expected_ars2_subtotal = str(prior_saldo_ars + Decimal("700.00"))
    after_ars2 = await _get_movimiento_by_id(
        client, secretaria_headers, ars2["id"], caja_id=caja_id
    )
    assert after_ars2["subtotal"] == expected_ars2_subtotal, (
        f"ARS stream recalculated: expected {expected_ars2_subtotal}, got {after_ars2['subtotal']}"
    )

    # USD stream must be untouched (usd1 subtotal is exactly what was returned at creation)
    after_usd1 = await _get_movimiento_by_id(
        client, secretaria_headers, usd1["id"], caja_id=caja_id
    )
    assert after_usd1["subtotal"] == usd1["subtotal"], (
        f"USD stream should not be affected by ARS patch. Got: {after_usd1['subtotal']}"
    )


@pytest.mark.asyncio
async def test_delete_ars_does_not_affect_usd_stream(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """DELETE of an ARS row must leave the USD stream completely untouched."""
    suffix = uuid4().hex[:8]
    caja_id = 10

    ars1 = await _create_movimiento(
        client, secretaria_headers,
        descripcion=f"ARS del {suffix}", monto="400.00", tipo="entrada",
        caja_id=caja_id, moneda="ARS",
    )
    usd1 = await _create_movimiento(
        client, secretaria_headers,
        descripcion=f"USD keep {suffix}", monto="75.00", tipo="entrada",
        caja_id=caja_id, moneda="USD",
    )

    delete_resp = await client.delete(
        f"/api/v1/cajas/{caja_id}/movimientos/{ars1['id']}",
        headers=secretaria_headers,
    )
    assert delete_resp.status_code == 204

    after_usd1 = await _get_movimiento_by_id(
        client, secretaria_headers, usd1["id"], caja_id=caja_id
    )
    # usd1 subtotal at creation time must remain unchanged after ARS delete
    assert after_usd1["subtotal"] == usd1["subtotal"], (
        f"USD stream should be untouched after ARS delete. Got: {after_usd1['subtotal']}"
    )
