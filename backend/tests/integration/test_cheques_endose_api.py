"""
T011 — TDD: POST /api/v1/cajas/{id}/movimientos/{mid}/endosar (feature 011, US1).

Obligatorio por constitución: subtotales/saldo y RBAC.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from .cheque_helpers import get_movimiento, insert_cheque

URL = "/api/v1/cajas/{caja_id}/movimientos/{movimiento_id}/endosar"


@pytest.fixture
async def otra_caja(client: AsyncClient, secretaria_headers: dict[str, str]) -> dict:
    response = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": f"Destino {uuid4().hex[:12]}"},
        headers=secretaria_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _saldo(client: AsyncClient, headers: dict, caja_id: int) -> tuple[Decimal, Decimal]:
    response = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=headers)
    assert response.status_code == 200
    body = response.json()
    return Decimal(body["saldo_ars"]), Decimal(body["saldo_usd"])


async def _endosar(
    client: AsyncClient, headers: dict, caja_id: int, movimiento_id: int, destino: int
):
    return await client.post(
        URL.format(caja_id=caja_id, movimiento_id=movimiento_id),
        json={"caja_destino_id": destino},
        headers=headers,
    )


async def _movimientos(client: AsyncClient, headers: dict, caja_id: int) -> list[dict]:
    response = await client.get(f"/api/v1/cajas/{caja_id}/movimientos", headers=headers)
    assert response.status_code == 200
    return response.json()["items"]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tipo", "moneda", "origen_ars", "origen_usd", "destino_ars", "destino_usd", "tipo_destino"),
    [
        ("entrada", "ARS", "500.00", "0.00", "-500.00", "0.00", "salida"),
        ("salida", "ARS", "-500.00", "0.00", "500.00", "0.00", "entrada"),
        ("entrada", "USD", "0.00", "500.00", "0.00", "-500.00", "salida"),
        ("salida", "USD", "0.00", "-500.00", "0.00", "500.00", "entrada"),
    ],
)
async def test_endosar_updates_both_cajas_with_the_inverse_movement(
    client: AsyncClient,
    secretaria_headers: dict,
    fresh_caja: dict,
    otra_caja: dict,
    tipo: str,
    moneda: str,
    origen_ars: str,
    origen_usd: str,
    destino_ars: str,
    destino_usd: str,
    tipo_destino: str,
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"], tipo=tipo, moneda=moneda, monto="500.00")
    # pendiente: sin impacto
    assert await _saldo(client, secretaria_headers, fresh_caja["id"]) == (Decimal(0), Decimal(0))

    response = await _endosar(
        client, secretaria_headers, fresh_caja["id"], cheque_id, otra_caja["id"]
    )

    assert response.status_code == 200, response.text
    body = response.json()
    cheque = body["cheque"]
    assert cheque["id"] == cheque_id
    assert cheque["estado"] == "liquidado"
    assert cheque["endosado_a"]["id"] == otra_caja["id"]
    assert cheque["editable"] is False
    assert cheque["liquidable"] is False
    assert cheque["endosable"] is False
    assert cheque["subtotal"] is not None

    destino = body["movimiento_destino"]
    assert destino["tipo"] == tipo_destino
    assert destino["moneda"] == moneda
    assert destino["monto"] == "500.00"
    assert destino["instrumento"] == "ninguno"
    assert destino["caja"]["id"] == otra_caja["id"]
    assert destino["endose_origen"]["cheque_id"] == cheque_id
    assert destino["endose_origen"]["caja"]["id"] == fresh_caja["id"]
    assert destino["editable"] is False
    assert destino["descripcion"].startswith("Endose cheque: cheque de prueba (Caja ")

    assert await _saldo(client, secretaria_headers, fresh_caja["id"]) == (
        Decimal(origen_ars),
        Decimal(origen_usd),
    )
    assert await _saldo(client, secretaria_headers, otra_caja["id"]) == (
        Decimal(destino_ars),
        Decimal(destino_usd),
    )


@pytest.mark.asyncio
async def test_endosar_works_before_the_fecha_de_liquidacion_and_appears_in_both_historiales(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    # fecha_liquidacion lejana (2030): Liquidar no estaría permitido, Endose sí.
    cheque_id = insert_cheque(fresh_caja["id"], tipo="entrada", monto="500.00")

    response = await _endosar(
        client, secretaria_headers, fresh_caja["id"], cheque_id, otra_caja["id"]
    )
    assert response.status_code == 200, response.text

    origen_items = await _movimientos(client, secretaria_headers, fresh_caja["id"])
    assert [m["id"] for m in origen_items] == [cheque_id]
    assert origen_items[0]["endosado_a"]["id"] == otra_caja["id"]
    assert origen_items[0]["subtotal"] == "500.00"

    destino_items = await _movimientos(client, secretaria_headers, otra_caja["id"])
    assert len(destino_items) == 1
    assert destino_items[0]["subtotal"] == "-500.00"
    assert destino_items[0]["endose_origen"]["cheque_id"] == cheque_id


@pytest.mark.asyncio
async def test_endosar_persists_audit_fields(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])
    response = await _endosar(
        client, secretaria_headers, fresh_caja["id"], cheque_id, otra_caja["id"]
    )
    assert response.status_code == 200, response.text

    cheque = get_movimiento(cheque_id)
    assert cheque.fecha_liquidado is not None
    assert cheque.endosado_a_caja_id == otra_caja["id"]
    assert cheque.updated_by is not None


# ---------------------------------------------------------------------------
# Auth / RBAC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endosar_requires_authentication(
    client: AsyncClient, fresh_caja: dict, otra_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])
    response = await client.post(
        URL.format(caja_id=fresh_caja["id"], movimiento_id=cheque_id),
        json={"caja_destino_id": otra_caja["id"]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_escribano_cannot_endosar(
    client: AsyncClient,
    escribano_headers: dict,
    secretaria_headers: dict,
    fresh_caja: dict,
    otra_caja: dict,
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])
    response = await _endosar(
        client, escribano_headers, fresh_caja["id"], cheque_id, otra_caja["id"]
    )
    assert response.status_code == 403
    assert get_movimiento(cheque_id).fecha_liquidado is None
    assert await _saldo(client, secretaria_headers, otra_caja["id"]) == (Decimal(0), Decimal(0))


# ---------------------------------------------------------------------------
# 404 / 409 / 422
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_origin_caja_is_404(
    client: AsyncClient, secretaria_headers: dict, otra_caja: dict
) -> None:
    response = await _endosar(client, secretaria_headers, 32_000, 1, otra_caja["id"])
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unknown_or_foreign_cheque_is_404(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    cheque_en_otra = insert_cheque(otra_caja["id"])

    unknown = await _endosar(
        client, secretaria_headers, fresh_caja["id"], 999_999_999, otra_caja["id"]
    )
    assert unknown.status_code == 404
    foreign = await _endosar(
        client, secretaria_headers, fresh_caja["id"], cheque_en_otra, otra_caja["id"]
    )
    assert foreign.status_code == 404
    assert get_movimiento(cheque_en_otra).fecha_liquidado is None


@pytest.mark.asyncio
async def test_common_movement_is_404(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    created = await client.post(
        f"/api/v1/cajas/{fresh_caja['id']}/movimientos",
        json={"descripcion": "comun", "monto": "10.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )
    assert created.status_code == 201
    response = await _endosar(
        client,
        secretaria_headers,
        fresh_caja["id"],
        created.json()["movimiento"]["id"],
        otra_caja["id"],
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unknown_destination_caja_is_404(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])
    response = await _endosar(client, secretaria_headers, fresh_caja["id"], cheque_id, 32_000)
    assert response.status_code == 404
    assert get_movimiento(cheque_id).fecha_liquidado is None


@pytest.mark.asyncio
async def test_second_endose_is_409_and_balances_are_not_duplicated(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"], monto="500.00")
    first = await _endosar(
        client, secretaria_headers, fresh_caja["id"], cheque_id, otra_caja["id"]
    )
    assert first.status_code == 200
    second = await _endosar(
        client, secretaria_headers, fresh_caja["id"], cheque_id, otra_caja["id"]
    )
    assert second.status_code == 409

    assert await _saldo(client, secretaria_headers, fresh_caja["id"]) == (
        Decimal("500.00"),
        Decimal(0),
    )
    assert await _saldo(client, secretaria_headers, otra_caja["id"]) == (
        Decimal("-500.00"),
        Decimal(0),
    )


@pytest.mark.asyncio
async def test_already_liquidated_cheque_is_409(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    from datetime import date

    cheque_id = insert_cheque(fresh_caja["id"], fecha_liquidacion=date(2020, 1, 1))
    liquidated = await client.post(
        f"/api/v1/cajas/{fresh_caja['id']}/movimientos/{cheque_id}/liquidar",
        headers=secretaria_headers,
    )
    assert liquidated.status_code == 200

    response = await _endosar(
        client, secretaria_headers, fresh_caja["id"], cheque_id, otra_caja["id"]
    )
    assert response.status_code == 409
    assert await _saldo(client, secretaria_headers, otra_caja["id"]) == (Decimal(0), Decimal(0))


@pytest.mark.asyncio
async def test_destination_equal_to_origin_is_422(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])
    response = await _endosar(
        client, secretaria_headers, fresh_caja["id"], cheque_id, fresh_caja["id"]
    )
    assert response.status_code == 422
    assert get_movimiento(cheque_id).fecha_liquidado is None


@pytest.mark.asyncio
async def test_archived_destination_is_422(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    archived = await client.post(
        f"/api/v1/cajas/{otra_caja['id']}/archive", headers=secretaria_headers
    )
    assert archived.status_code == 200, archived.text
    cheque_id = insert_cheque(fresh_caja["id"])

    response = await _endosar(
        client, secretaria_headers, fresh_caja["id"], cheque_id, otra_caja["id"]
    )
    assert response.status_code == 422
    assert get_movimiento(cheque_id).fecha_liquidado is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"caja_destino_id": 0},
        {"caja_destino_id": -3},
        {"caja_destino_id": "abc"},
        {"caja_destino_id": None},
        {"caja_destino_id": 2, "descripcion": "libre"},
        {"caja_destino_id": 2, "monto": "1.00"},
    ],
)
async def test_invalid_payload_is_422(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, payload: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])
    response = await client.post(
        URL.format(caja_id=fresh_caja["id"], movimiento_id=cheque_id),
        json=payload,
        headers=secretaria_headers,
    )
    assert response.status_code == 422
    assert get_movimiento(cheque_id).fecha_liquidado is None


# ---------------------------------------------------------------------------
# FR-019: registros finales
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endorsed_cheque_and_destination_movement_cannot_be_edited_or_deleted(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"], monto="500.00")
    response = await _endosar(
        client, secretaria_headers, fresh_caja["id"], cheque_id, otra_caja["id"]
    )
    assert response.status_code == 200
    destino_id = response.json()["movimiento_destino"]["id"]

    for caja_id, mov_id in ((fresh_caja["id"], cheque_id), (otra_caja["id"], destino_id)):
        url = f"/api/v1/cajas/{caja_id}/movimientos/{mov_id}"
        patched = await client.patch(url, json={"descripcion": "otra"}, headers=secretaria_headers)
        assert patched.status_code == 409, patched.text
        deleted = await client.delete(url, headers=secretaria_headers)
        assert deleted.status_code == 409, deleted.text

    assert await _saldo(client, secretaria_headers, fresh_caja["id"]) == (
        Decimal("500.00"),
        Decimal(0),
    )
    assert await _saldo(client, secretaria_headers, otra_caja["id"]) == (
        Decimal("-500.00"),
        Decimal(0),
    )
