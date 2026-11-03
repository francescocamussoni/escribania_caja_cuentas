"""
T043 — TDD: GET /api/v1/cheques?categoria=aptos|proximos (feature 010, US3).

Sección "Cheques": pendientes de TODAS las cajas, en dos categorías. La DB de tests es
compartida (otros tests dejan cheques), así que las aserciones se limitan a los ids de
cada test. "Hoy" se fija parcheando `today_ar` en la ruta.
"""

from datetime import date, datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from .cheque_helpers import insert_cheque

URL = "/api/v1/cheques"
# Earlier than the default fixture date (2030) so other tests' cheques fall outside both
# categories. End of month: 2029-03-31.
HOY = date(2029, 3, 10)


def _fixed_today():
    return patch("app.api.routes.cheques.today_ar", return_value=HOY)


async def _new_caja(client: AsyncClient, headers: dict) -> dict:
    response = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": f"Cheques sec {uuid4().hex[:12]}"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _ids(client: AsyncClient, headers: dict, categoria: str) -> list[int]:
    """All ids of a category, walking every page (the shared DB may hold many rows)."""
    ids: list[int] = []
    page = 1
    while True:
        with _fixed_today():
            response = await client.get(
                URL, params={"categoria": categoria, "page": page}, headers=headers
            )
        assert response.status_code == 200, response.text
        body = response.json()
        ids.extend(item["id"] for item in body["items"])
        if page >= body["total_pages"]:
            return ids
        page += 1


async def _items(client: AsyncClient, headers: dict, categoria: str) -> dict[int, dict]:
    items: dict[int, dict] = {}
    page = 1
    while True:
        with _fixed_today():
            response = await client.get(
                URL, params={"categoria": categoria, "page": page}, headers=headers
            )
        body = response.json()
        items.update({item["id"]: item for item in body["items"]})
        if page >= body["total_pages"]:
            return items
        page += 1


@pytest.mark.asyncio
async def test_category_boundaries(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    pasado = insert_cheque(caja_id, fecha_liquidacion=date(2029, 2, 1))
    hoy = insert_cheque(caja_id, fecha_liquidacion=HOY)
    manana = insert_cheque(caja_id, fecha_liquidacion=date(2029, 3, 11))
    fin_de_mes = insert_cheque(caja_id, fecha_liquidacion=date(2029, 3, 31))
    mes_siguiente = insert_cheque(caja_id, fecha_liquidacion=date(2029, 4, 1))
    mine = {pasado, hoy, manana, fin_de_mes, mes_siguiente}

    aptos = [i for i in await _ids(client, secretaria_headers, "aptos") if i in mine]
    proximos = [i for i in await _ids(client, secretaria_headers, "proximos") if i in mine]

    assert aptos == [pasado, hoy]
    assert proximos == [manana, fin_de_mes]
    assert mes_siguiente not in aptos + proximos


@pytest.mark.asyncio
async def test_excludes_liquidated_cheques(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    pendiente = insert_cheque(caja_id, fecha_liquidacion=date(2029, 3, 1))
    liquidado = insert_cheque(
        caja_id,
        fecha_liquidacion=date(2029, 3, 1),
        fecha_liquidado=datetime.now(timezone.utc),
        subtotal="100.00",
    )

    aptos = await _ids(client, secretaria_headers, "aptos")

    assert pendiente in aptos
    assert liquidado not in aptos


@pytest.mark.asyncio
async def test_lists_cheques_of_several_cajas_including_archived(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    otra = await _new_caja(client, secretaria_headers)
    archivada = await _new_caja(client, secretaria_headers)
    a = insert_cheque(fresh_caja["id"], fecha_liquidacion=date(2029, 3, 2))
    b = insert_cheque(otra["id"], fecha_liquidacion=date(2029, 3, 3))
    c = insert_cheque(archivada["id"], fecha_liquidacion=date(2029, 3, 4))
    archive = await client.post(
        f"/api/v1/cajas/{archivada['id']}/archive", json={}, headers=secretaria_headers
    )
    assert archive.status_code == 200, archive.text

    by_id = await _items(client, secretaria_headers, "aptos")

    assert {a, b, c} <= set(by_id)
    assert by_id[a]["caja"]["id"] == fresh_caja["id"]
    assert by_id[b]["caja"]["id"] == otra["id"]
    assert by_id[c]["caja"]["id"] == archivada["id"]
    assert by_id[a]["caja"]["nombre"] == fresh_caja["nombre"]


@pytest.mark.asyncio
async def test_ordered_by_fecha_liquidacion_then_id(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    tarde = insert_cheque(caja_id, fecha_liquidacion=date(2029, 3, 20))
    temprano_1 = insert_cheque(caja_id, fecha_liquidacion=date(2029, 3, 12))
    temprano_2 = insert_cheque(caja_id, fecha_liquidacion=date(2029, 3, 12))
    mine = {tarde, temprano_1, temprano_2}

    proximos = [i for i in await _ids(client, secretaria_headers, "proximos") if i in mine]

    assert proximos == [temprano_1, temprano_2, tarde]


@pytest.mark.asyncio
async def test_paginates_with_fixed_page_size_20(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    for _ in range(23):
        insert_cheque(caja_id, fecha_liquidacion=date(1999, 1, 1))

    with _fixed_today():
        page1 = await client.get(
            URL, params={"categoria": "aptos", "page": 1}, headers=secretaria_headers
        )
        page2 = await client.get(
            URL, params={"categoria": "aptos", "page": 2}, headers=secretaria_headers
        )

    body1, body2 = page1.json(), page2.json()
    assert body1["page_size"] == 20
    assert len(body1["items"]) == 20
    assert body1["total_items"] >= 23
    assert body1["total_pages"] >= 2
    assert body2["page"] == 2
    assert 1 <= len(body2["items"]) <= 20
    ids1 = {i["id"] for i in body1["items"]}
    ids2 = {i["id"] for i in body2["items"]}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"categoria": "otra"},
        {},
        {"categoria": "aptos", "page": 0},
        {"categoria": "aptos", "page": "x"},
    ],
)
async def test_invalid_query_is_422(
    client: AsyncClient, secretaria_headers: dict, params: dict
) -> None:
    response = await client.get(URL, params=params, headers=secretaria_headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_liquidable_depends_on_the_role(
    client: AsyncClient,
    secretaria_headers: dict,
    escribano_headers: dict,
    fresh_caja: dict,
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"], fecha_liquidacion=date(2029, 3, 5))

    sec_item = (await _items(client, secretaria_headers, "aptos"))[cheque_id]
    esc_item = (await _items(client, escribano_headers, "aptos"))[cheque_id]
    assert sec_item["liquidable"] is True
    assert esc_item["liquidable"] is False


@pytest.mark.asyncio
async def test_without_token_is_401(client: AsyncClient) -> None:
    response = await client.get(URL, params={"categoria": "aptos"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_never_exposes_a_subtotal(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"], fecha_liquidacion=date(2029, 3, 5))

    item = (await _items(client, secretaria_headers, "aptos"))[cheque_id]
    assert item["subtotal"] is None
    assert item["estado"] == "pendiente"
