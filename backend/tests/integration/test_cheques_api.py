"""
T020 — TDD: POST /api/v1/cajas/{id}/movimientos con cheque/echeque (feature 010, US1).

Cada test usa una caja nueva (`fresh_caja`) para ser independiente de datos previos.
"""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.core.dates import today_ar


def future(days: int = 5) -> str:
    return (today_ar() + timedelta(days=days)).isoformat()


async def _saldo(client: AsyncClient, headers: dict, caja_id: int) -> dict:
    response = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=headers)
    assert response.status_code == 200
    return response.json()


async def _post(client: AsyncClient, headers: dict, caja_id: int, **overrides):
    payload = {
        "descripcion": "Cheque cliente",
        "monto": "500.00",
        "tipo": "entrada",
        "moneda": "ARS",
        "instrumento": "cheque",
        "fecha_liquidacion": future(),
    }
    payload.update(overrides)
    payload = {k: v for k, v in payload.items() if v is not None}
    return await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos", json=payload, headers=headers
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("instrumento", ["cheque", "echeque"])
@pytest.mark.parametrize("tipo", ["entrada", "salida"])
async def test_create_pending_cheque_has_no_subtotal_and_does_not_change_saldo(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, instrumento: str, tipo: str
) -> None:
    caja_id = fresh_caja["id"]
    base = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": "base", "monto": "1000.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )
    assert base.status_code == 201
    fecha = future(7)

    response = await _post(
        client, secretaria_headers, caja_id,
        instrumento=instrumento, tipo=tipo, fecha_liquidacion=fecha,
    )

    assert response.status_code == 201, response.text
    mov = response.json()["movimiento"]
    assert mov["instrumento"] == instrumento
    assert mov["estado"] == "pendiente"
    assert mov["subtotal"] is None
    assert mov["fecha_liquidacion"] == fecha
    assert mov["fecha_liquidado"] is None
    assert mov["liquidable"] is True
    assert mov["fecha"] == mov["fecha_carga"]
    assert response.json()["complementario"] is None

    saldo = await _saldo(client, secretaria_headers, caja_id)
    assert saldo["saldo_ars"] == "1000.00"


@pytest.mark.asyncio
async def test_create_cheque_in_usd_does_not_affect_either_saldo(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]

    response = await _post(client, secretaria_headers, caja_id, moneda="USD", monto="80.00")

    assert response.status_code == 201
    assert response.json()["movimiento"]["moneda"] == "USD"
    saldo = await _saldo(client, secretaria_headers, caja_id)
    assert saldo["saldo_ars"] == "0.00"
    assert saldo["saldo_usd"] == "0.00"


@pytest.mark.asyncio
async def test_pending_cheque_is_not_listed_in_movimientos(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    created = await _post(client, secretaria_headers, caja_id)
    assert created.status_code == 201

    listing = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos", headers=secretaria_headers
    )

    assert listing.json()["total_items"] == 0


@pytest.mark.asyncio
async def test_common_movement_after_pending_cheque_ignores_the_cheque(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _post(client, secretaria_headers, caja_id, monto="900.00")

    common = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": "comun", "monto": "100.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )

    assert common.json()["movimiento"]["subtotal"] == "100.00"
    assert common.json()["movimiento"]["instrumento"] == "ninguno"
    assert common.json()["movimiento"]["estado"] is None


@pytest.mark.asyncio
async def test_cheque_uses_fecha_manual_as_fecha_de_carga(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    response = await _post(
        client, secretaria_headers, fresh_caja["id"], fecha_manual="2026-01-10"
    )

    assert response.status_code == 201
    mov = response.json()["movimiento"]
    assert mov["fecha_carga"].startswith("2026-01-10T09:00:00")
    assert mov["fecha"] == mov["fecha_carga"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"fecha_liquidacion": None},  # obligatoria
        {"fecha_liquidacion": "2020-01-01"},  # pasada
        {"fecha_liquidacion": "2026-02-30"},  # no calendario
        {"fecha_liquidacion": "10/11/2030"},  # formato
        {"registrar_complementario": True},  # sin "Entrada y Salida"
        {"instrumento": "pagare"},  # instrumento inválido
    ],
)
async def test_invalid_cheque_payloads_are_rejected_with_422(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, overrides: dict
) -> None:
    response = await _post(client, secretaria_headers, fresh_caja["id"], **overrides)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_fecha_liquidacion_today_is_rejected(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    response = await _post(
        client, secretaria_headers, fresh_caja["id"], fecha_liquidacion=today_ar().isoformat()
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_fecha_liquidacion_without_instrumento_is_rejected(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    response = await client.post(
        f"/api/v1/cajas/{fresh_caja['id']}/movimientos",
        json={
            "descripcion": "x", "monto": "1.00", "tipo": "entrada",
            "fecha_liquidacion": future(),
        },
        headers=secretaria_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_common_movement_payload_is_unchanged(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    response = await client.post(
        f"/api/v1/cajas/{fresh_caja['id']}/movimientos",
        json={"descripcion": "Honorarios", "monto": "15000.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )
    assert response.status_code == 201
    mov = response.json()["movimiento"]
    assert mov["subtotal"] == "15000.00"
    assert mov["instrumento"] == "ninguno"
    assert mov["liquidable"] is False


@pytest.mark.asyncio
async def test_escribano_cannot_create_cheque(
    client: AsyncClient, escribano_headers: dict, fresh_caja: dict
) -> None:
    response = await _post(client, escribano_headers, fresh_caja["id"])
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_cheque_without_token_is_401(client: AsyncClient, fresh_caja: dict) -> None:
    response = await client.post(
        f"/api/v1/cajas/{fresh_caja['id']}/movimientos",
        json={
            "descripcion": "x", "monto": "1.00", "tipo": "entrada",
            "instrumento": "cheque", "fecha_liquidacion": future(),
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_cheque_on_unknown_caja_is_404(
    client: AsyncClient, secretaria_headers: dict
) -> None:
    response = await _post(client, secretaria_headers, 999999)
    assert response.status_code == 404
