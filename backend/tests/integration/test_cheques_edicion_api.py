"""
T066 — TDD: PATCH / DELETE de cheques por API (feature 010, US5).

Obligatorio por constitución: subtotales/saldo y RBAC.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.dates import today_ar

from .cheque_helpers import get_movimiento, insert_cheque

BASE = "/api/v1/cajas/{caja_id}/movimientos/{movimiento_id}"
FUTURO = "2999-06-01"


async def _patch(client, headers, caja_id, movimiento_id, body):
    return await client.patch(
        BASE.format(caja_id=caja_id, movimiento_id=movimiento_id), json=body, headers=headers
    )


async def _delete(client, headers, caja_id, movimiento_id):
    return await client.delete(
        BASE.format(caja_id=caja_id, movimiento_id=movimiento_id), headers=headers
    )


async def _saldo(client, headers, caja_id) -> tuple[Decimal, Decimal]:
    body = (await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=headers)).json()
    return Decimal(body["saldo_ars"]), Decimal(body["saldo_usd"])


async def _common(client, headers, caja_id, tipo, monto) -> int:
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": "comun", "monto": monto, "tipo": tipo},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["movimiento"]["id"]


def _liquidated(caja_id: int, **kwargs) -> int:
    return insert_cheque(
        caja_id,
        fecha_liquidado=datetime.now(timezone.utc),
        subtotal=kwargs.pop("subtotal", "100.00"),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# PATCH — pendiente
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_pending_cheque_does_not_change_the_saldo(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00")
    cheque_id = insert_cheque(caja_id, monto="100.00", tipo="entrada")

    response = await _patch(
        client,
        secretaria_headers,
        caja_id,
        cheque_id,
        {
            "monto": "999.00",
            "tipo": "salida",
            "moneda": "USD",
            "descripcion": "editado",
            "instrumento": "echeque",
            "fecha_liquidacion": FUTURO,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["monto"] == "999.00"
    assert body["tipo"] == "salida"
    assert body["moneda"] == "USD"
    assert body["instrumento"] == "echeque"
    assert body["fecha_liquidacion"] == FUTURO
    assert body["estado"] == "pendiente"
    assert body["subtotal"] is None
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("1000.00"), Decimal("0"))
    stored = get_movimiento(cheque_id)
    assert stored.subtotal is None and stored.fecha_liquidado is None


@pytest.mark.asyncio
@pytest.mark.parametrize("instrumento", ["cheque", "echeque"])
async def test_switch_between_cheque_and_echeque(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, instrumento: str
) -> None:
    other = "echeque" if instrumento == "cheque" else "cheque"
    cheque_id = insert_cheque(fresh_caja["id"], instrumento=other)

    response = await _patch(
        client, secretaria_headers, fresh_caja["id"], cheque_id, {"instrumento": instrumento}
    )

    assert response.status_code == 200
    assert response.json()["instrumento"] == instrumento


# ---------------------------------------------------------------------------
# PATCH — validaciones
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_instrumento_ninguno_is_422(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])

    response = await _patch(
        client, secretaria_headers, fresh_caja["id"], cheque_id, {"instrumento": "ninguno"}
    )

    assert response.status_code == 422
    assert get_movimiento(cheque_id).instrumento == "cheque"


@pytest.mark.asyncio
@pytest.mark.parametrize("fecha", ["2020-01-01", today_ar().isoformat(), "no-fecha"])
async def test_fecha_liquidacion_not_after_today_or_malformed_is_422(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, fecha: str
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])

    response = await _patch(
        client, secretaria_headers, fresh_caja["id"], cheque_id, {"fecha_liquidacion": fecha}
    )

    assert response.status_code == 422
    assert get_movimiento(cheque_id).fecha_liquidacion == date(2030, 1, 15)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body", [{"instrumento": "cheque"}, {"fecha_liquidacion": FUTURO}]
)
async def test_common_movement_with_instrument_fields_is_400(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, body: dict
) -> None:
    caja_id = fresh_caja["id"]
    comun_id = await _common(client, secretaria_headers, caja_id, "entrada", "50.00")

    response = await _patch(client, secretaria_headers, caja_id, comun_id, body)

    assert response.status_code == 400
    stored = get_movimiento(comun_id)
    assert stored.instrumento == "ninguno" and stored.fecha_liquidacion is None
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("50.00"), Decimal("0"))


@pytest.mark.asyncio
async def test_fecha_liquidacion_of_a_liquidated_cheque_is_400(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    cheque_id = _liquidated(fresh_caja["id"], monto="100.00")

    response = await _patch(
        client, secretaria_headers, fresh_caja["id"], cheque_id, {"fecha_liquidacion": FUTURO}
    )

    assert response.status_code == 400
    assert get_movimiento(cheque_id).fecha_liquidacion == date(2030, 1, 15)


# ---------------------------------------------------------------------------
# PATCH — liquidado: cascada
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_editing_a_liquidated_cheque_recalculates_the_stream(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00")
    cheque_id = insert_cheque(
        caja_id, tipo="entrada", monto="100.00", fecha_liquidacion=date(2020, 1, 1)
    )
    liquidated = await client.post(
        BASE.format(caja_id=caja_id, movimiento_id=cheque_id) + "/liquidar",
        headers=secretaria_headers,
    )
    assert liquidated.status_code == 200
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("1100.00"), Decimal("0"))

    response = await _patch(
        client, secretaria_headers, caja_id, cheque_id, {"monto": "300.00"}
    )

    assert response.status_code == 200
    assert response.json()["subtotal"] == "1300.00"
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("1300.00"), Decimal("0"))


@pytest.mark.asyncio
async def test_changing_moneda_of_a_liquidated_cheque_moves_it_between_streams(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    cheque_id = insert_cheque(
        caja_id, tipo="entrada", monto="100.00", fecha_liquidacion=date(2020, 1, 1)
    )
    await client.post(
        BASE.format(caja_id=caja_id, movimiento_id=cheque_id) + "/liquidar",
        headers=secretaria_headers,
    )

    response = await _patch(client, secretaria_headers, caja_id, cheque_id, {"moneda": "USD"})

    assert response.status_code == 200
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("0"), Decimal("100.00"))


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_pending_cheque_removes_it_without_touching_the_saldo(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _common(client, secretaria_headers, caja_id, "entrada", "400.00")
    cheque_id = insert_cheque(caja_id, monto="50.00")

    response = await _delete(client, secretaria_headers, caja_id, cheque_id)

    assert response.status_code == 204
    pendientes = await client.get(
        f"/api/v1/cajas/{caja_id}/cheques-pendientes", headers=secretaria_headers
    )
    assert pendientes.json()["items"] == []
    futuro = (
        await client.get(f"/api/v1/cajas/{caja_id}/saldo-futuro", headers=secretaria_headers)
    ).json()
    assert all(m["filas"] == [] for m in futuro["monedas"])
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("400.00"), Decimal("0"))


@pytest.mark.asyncio
async def test_delete_liquidated_cheque_recalculates(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _common(client, secretaria_headers, caja_id, "entrada", "400.00")
    cheque_id = insert_cheque(
        caja_id, tipo="entrada", monto="50.00", fecha_liquidacion=date(2020, 1, 1)
    )
    await client.post(
        BASE.format(caja_id=caja_id, movimiento_id=cheque_id) + "/liquidar",
        headers=secretaria_headers,
    )
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("450.00"), Decimal("0"))

    response = await _delete(client, secretaria_headers, caja_id, cheque_id)

    assert response.status_code == 204
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("400.00"), Decimal("0"))


# ---------------------------------------------------------------------------
# RBAC / 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escribano_cannot_edit_or_delete_cheques(
    client: AsyncClient, escribano_headers: dict, fresh_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])

    patch_response = await _patch(
        client, escribano_headers, fresh_caja["id"], cheque_id, {"instrumento": "echeque"}
    )
    delete_response = await _delete(client, escribano_headers, fresh_caja["id"], cheque_id)

    assert patch_response.status_code == 403
    assert delete_response.status_code == 403
    stored = get_movimiento(cheque_id)
    assert stored.instrumento == "cheque"


@pytest.mark.asyncio
async def test_unknown_cheque_is_404(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    patch_response = await _patch(
        client, secretaria_headers, fresh_caja["id"], 99999999, {"instrumento": "cheque"}
    )
    delete_response = await _delete(client, secretaria_headers, fresh_caja["id"], 99999999)

    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


@pytest.mark.asyncio
async def test_without_token_is_401(client: AsyncClient, fresh_caja: dict) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])

    patch_response = await client.patch(
        BASE.format(caja_id=fresh_caja["id"], movimiento_id=cheque_id), json={"monto": "1.00"}
    )
    delete_response = await client.delete(
        BASE.format(caja_id=fresh_caja["id"], movimiento_id=cheque_id)
    )

    assert patch_response.status_code == 401
    assert delete_response.status_code == 401
