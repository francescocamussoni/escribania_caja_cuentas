"""
T021 — TDD: GET /api/v1/cajas/{id}/cheques-pendientes (feature 010, US1).

Bloque "cheques pendientes" arriba del historial en Registro y Consulta.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from .cheque_helpers import insert_cheque

URL = "/api/v1/cajas/{caja_id}/cheques-pendientes"


@pytest.mark.asyncio
async def test_lists_only_pending_ordered_by_fecha_liquidacion_then_id(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    tarde = insert_cheque(caja_id, fecha_liquidacion=date(2030, 3, 1))
    temprano_a = insert_cheque(caja_id, fecha_liquidacion=date(2030, 1, 1))
    temprano_b = insert_cheque(caja_id, fecha_liquidacion=date(2030, 1, 1))
    insert_cheque(
        caja_id,
        fecha_liquidacion=date(2030, 2, 1),
        fecha_liquidado=datetime.now(timezone.utc),
        subtotal="100.00",
    )  # liquidado: no aparece
    # Un movimiento común tampoco aparece
    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": "comun", "monto": "5.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )

    response = await client.get(URL.format(caja_id=caja_id), headers=secretaria_headers)

    assert response.status_code == 200
    body = response.json()
    assert [i["id"] for i in body["items"]] == [temprano_a, temprano_b, tarde]
    assert body["total_items"] == 3
    assert all(i["estado"] == "pendiente" and i["subtotal"] is None for i in body["items"])
    assert body["page_size"] == 20


@pytest.mark.asyncio
async def test_paginates_with_page_size_20(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    for _ in range(23):
        insert_cheque(caja_id)

    page1 = await client.get(URL.format(caja_id=caja_id), headers=secretaria_headers)
    page2 = await client.get(
        URL.format(caja_id=caja_id), params={"page": 2}, headers=secretaria_headers
    )

    assert len(page1.json()["items"]) == 20
    assert len(page2.json()["items"]) == 3
    assert page1.json()["total_pages"] == 2


@pytest.mark.asyncio
async def test_filters_by_moneda(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    insert_cheque(caja_id, moneda="ARS")
    usd = insert_cheque(caja_id, moneda="USD")

    response = await client.get(
        URL.format(caja_id=caja_id), params={"moneda": "USD"}, headers=secretaria_headers
    )

    assert [i["id"] for i in response.json()["items"]] == [usd]


@pytest.mark.asyncio
async def test_date_filters_apply_to_fecha_de_carga(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    viejo = insert_cheque(caja_id, fecha_override=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc))
    insert_cheque(caja_id, fecha_override=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc))

    response = await client.get(
        URL.format(caja_id=caja_id),
        params={"fecha_desde": "2026-01-01", "fecha_hasta": "2026-01-31"},
        headers=secretaria_headers,
    )

    assert [i["id"] for i in response.json()["items"]] == [viejo]


@pytest.mark.asyncio
async def test_invalid_date_range_is_400(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    response = await client.get(
        URL.format(caja_id=fresh_caja["id"]),
        params={"fecha_desde": "2026-02-01", "fecha_hasta": "2026-01-01"},
        headers=secretaria_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_unknown_caja_is_404(client: AsyncClient, secretaria_headers: dict) -> None:
    response = await client.get(URL.format(caja_id=999999), headers=secretaria_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_without_token_is_401(client: AsyncClient, fresh_caja: dict) -> None:
    response = await client.get(URL.format(caja_id=fresh_caja["id"]))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_escribano_can_read_and_items_are_not_liquidable(
    client: AsyncClient, escribano_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    insert_cheque(caja_id)

    response = await client.get(URL.format(caja_id=caja_id), headers=escribano_headers)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["liquidable"] is False
    assert item["editable"] is False


@pytest.mark.asyncio
async def test_secretaria_items_are_liquidable(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    insert_cheque(caja_id)

    response = await client.get(URL.format(caja_id=caja_id), headers=secretaria_headers)

    item = response.json()["items"][0]
    assert item["liquidable"] is True
    assert item["editable"] is True
    assert item["caja"]["id"] == caja_id


# ---------------------------------------------------------------------------
# Registro: `incluir_pendientes` mezcla los cheques pendientes en el listado
# ---------------------------------------------------------------------------

LIST_URL = "/api/v1/cajas/{caja_id}/movimientos"


@pytest.mark.asyncio
async def test_listing_excludes_pending_by_default_and_includes_them_on_request(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await client.post(
        LIST_URL.format(caja_id=caja_id),
        json={"descripcion": "comun", "monto": "5.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )
    pendiente = insert_cheque(caja_id)

    default = await client.get(LIST_URL.format(caja_id=caja_id), headers=secretaria_headers)
    mixto = await client.get(
        LIST_URL.format(caja_id=caja_id) + "?incluir_pendientes=true", headers=secretaria_headers
    )

    assert default.status_code == 200 and mixto.status_code == 200
    assert pendiente not in [i["id"] for i in default.json()["items"]]
    assert default.json()["total_items"] == 1
    assert mixto.json()["total_items"] == 2
    item = next(i for i in mixto.json()["items"] if i["id"] == pendiente)
    assert item["estado"] == "pendiente" and item["subtotal"] is None
    assert item["liquidable"] is True and item["editable"] is True


@pytest.mark.asyncio
async def test_pending_in_listing_does_not_change_balance_and_respects_filters(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    insert_cheque(caja_id, moneda="USD", monto="70.00")
    insert_cheque(caja_id, moneda="ARS", monto="30.00")

    saldo = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=secretaria_headers)
    usd = await client.get(
        LIST_URL.format(caja_id=caja_id) + "?incluir_pendientes=true&moneda=USD",
        headers=secretaria_headers,
    )

    assert saldo.json()["saldo_ars"] == "0.00" and saldo.json()["saldo_usd"] == "0.00"
    assert [i["moneda"] for i in usd.json()["items"]] == ["USD"]


@pytest.mark.asyncio
async def test_escribano_can_request_listing_with_pending(
    client: AsyncClient, escribano_headers: dict, fresh_caja: dict
) -> None:
    insert_cheque(fresh_caja["id"])

    response = await client.get(
        LIST_URL.format(caja_id=fresh_caja["id"]) + "?incluir_pendientes=true",
        headers=escribano_headers,
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["liquidable"] is False
    assert response.json()["items"][0]["editable"] is False
