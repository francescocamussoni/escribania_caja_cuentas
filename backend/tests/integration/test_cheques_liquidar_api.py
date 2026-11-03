"""
T036 — TDD: POST /api/v1/cajas/{id}/movimientos/{mid}/liquidar (feature 010, US2).

Obligatorio por constitución: subtotales/saldo y RBAC.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from .cheque_helpers import get_movimiento, insert_cheque

URL = "/api/v1/cajas/{caja_id}/movimientos/{movimiento_id}/liquidar"


async def _saldo(client: AsyncClient, headers: dict, caja_id: int) -> tuple[Decimal, Decimal]:
    response = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=headers)
    assert response.status_code == 200
    body = response.json()
    return Decimal(body["saldo_ars"]), Decimal(body["saldo_usd"])


async def _liquidar(client: AsyncClient, headers: dict, caja_id: int, movimiento_id: int):
    return await client.post(
        URL.format(caja_id=caja_id, movimiento_id=movimiento_id), headers=headers
    )


async def _common(client: AsyncClient, headers: dict, caja_id: int, tipo: str, monto: str):
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": "comun", "monto": monto, "tipo": tipo},
        headers=headers,
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tipo", "moneda", "esperado_ars", "esperado_usd"),
    [
        ("entrada", "ARS", Decimal("1250.00"), Decimal("0")),
        ("salida", "ARS", Decimal("750.00"), Decimal("0")),
        ("entrada", "USD", Decimal("1000.00"), Decimal("250.00")),
        ("salida", "USD", Decimal("1000.00"), Decimal("-250.00")),
    ],
)
async def test_liquidar_updates_the_saldo_of_its_currency_only(
    client: AsyncClient,
    secretaria_headers: dict,
    fresh_caja: dict,
    tipo: str,
    moneda: str,
    esperado_ars: Decimal,
    esperado_usd: Decimal,
) -> None:
    caja_id = fresh_caja["id"]
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00")
    cheque_id = insert_cheque(
        caja_id, tipo=tipo, monto="250.00", moneda=moneda, fecha_liquidacion=date(2020, 1, 1)
    )
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("1000.00"), Decimal("0"))

    response = await _liquidar(client, secretaria_headers, caja_id, cheque_id)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["estado"] == "liquidado"
    assert body["fecha_liquidado"] is not None
    assert body["liquidable"] is False
    assert Decimal(body["subtotal"]) == (
        esperado_ars if moneda == "ARS" else esperado_usd
    )
    assert await _saldo(client, secretaria_headers, caja_id) == (esperado_ars, esperado_usd)


@pytest.mark.asyncio
async def test_liquidated_cheque_appears_in_movimientos_with_subtotal_and_leaves_pending(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    cheque_id = insert_cheque(caja_id, tipo="entrada", monto="80.00", fecha_liquidacion=date(2020, 1, 1))

    await _liquidar(client, secretaria_headers, caja_id, cheque_id)

    historial = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos", headers=secretaria_headers
    )
    items = historial.json()["items"]
    assert [i["id"] for i in items] == [cheque_id]
    assert Decimal(items[0]["subtotal"]) == Decimal("80.00")
    assert items[0]["instrumento"] == "cheque"
    assert items[0]["estado"] == "liquidado"

    pendientes = await client.get(
        f"/api/v1/cajas/{caja_id}/cheques-pendientes", headers=secretaria_headers
    )
    assert pendientes.json()["items"] == []


@pytest.mark.asyncio
async def test_second_liquidation_is_409_and_balance_is_not_duplicated(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    cheque_id = insert_cheque(caja_id, tipo="entrada", monto="40.00", fecha_liquidacion=date(2020, 1, 1))

    first = await _liquidar(client, secretaria_headers, caja_id, cheque_id)
    second = await _liquidar(client, secretaria_headers, caja_id, cheque_id)

    assert first.status_code == 200
    assert second.status_code == 409
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("40.00"), Decimal("0"))


@pytest.mark.asyncio
async def test_common_movement_cannot_be_liquidated(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _common(client, secretaria_headers, caja_id, "entrada", "10.00")
    historial = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos", headers=secretaria_headers
    )
    comun_id = historial.json()["items"][0]["id"]

    response = await _liquidar(client, secretaria_headers, caja_id, comun_id)

    assert response.status_code == 404
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("10.00"), Decimal("0"))


@pytest.mark.asyncio
async def test_cheque_of_another_caja_is_404(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    other = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": f"Otra caja {uuid4().hex[:12]}"},
        headers=secretaria_headers,
    )
    assert other.status_code == 201, other.text
    other_id = other.json()["id"]
    cheque_id = insert_cheque(other_id, monto="10.00")

    response = await _liquidar(client, secretaria_headers, fresh_caja["id"], cheque_id)

    assert response.status_code == 404
    assert get_movimiento(cheque_id).fecha_liquidado is None


@pytest.mark.asyncio
async def test_unknown_caja_or_movimiento_is_404(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    assert (await _liquidar(client, secretaria_headers, 99999999, 1)).status_code == 404
    assert (await _liquidar(client, secretaria_headers, fresh_caja["id"], 99999999)).status_code == 404


@pytest.mark.asyncio
async def test_escribano_cannot_liquidar(
    client: AsyncClient, escribano_headers: dict, fresh_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])

    response = await _liquidar(client, escribano_headers, fresh_caja["id"], cheque_id)

    assert response.status_code == 403
    assert get_movimiento(cheque_id).fecha_liquidado is None


@pytest.mark.asyncio
async def test_liquidar_without_token_is_401(client: AsyncClient, fresh_caja: dict) -> None:
    cheque_id = insert_cheque(fresh_caja["id"])

    response = await client.post(
        URL.format(caja_id=fresh_caja["id"], movimiento_id=cheque_id)
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reaching_the_fecha_de_liquidacion_does_not_auto_liquidate(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    from datetime import date

    caja_id = fresh_caja["id"]
    # A cheque whose fecha de liquidación already passed stays pending until a person acts.
    cheque_id = insert_cheque(caja_id, fecha_liquidacion=date(2020, 1, 1), monto="99.00")

    pendientes = await client.get(
        f"/api/v1/cajas/{caja_id}/cheques-pendientes", headers=secretaria_headers
    )

    assert [i["id"] for i in pendientes.json()["items"]] == [cheque_id]
    assert pendientes.json()["items"][0]["liquidable"] is True
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("0"), Decimal("0"))


@pytest.mark.asyncio
async def test_failure_during_liquidation_leaves_the_cheque_pending(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    cheque_id = insert_cheque(caja_id, monto="60.00", fecha_liquidacion=date(2020, 1, 1))

    with patch(
        "app.services.movimiento_service.MovimientoService.recalculate_subtotals",
        side_effect=RuntimeError("boom"),
    ):
        response = await _liquidar(client, secretaria_headers, caja_id, cheque_id)

    assert response.status_code == 500
    assert "boom" not in response.text
    cheque = get_movimiento(cheque_id)
    assert cheque.fecha_liquidado is None
    assert cheque.subtotal is None
    assert await _saldo(client, secretaria_headers, caja_id) == (Decimal("0"), Decimal("0"))


@pytest.mark.asyncio
async def test_cannot_liquidate_before_the_fecha_de_liquidacion(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    from datetime import timedelta

    from app.core.dates import today_ar

    caja_id = fresh_caja["id"]
    manana = insert_cheque(caja_id, monto="10.00", fecha_liquidacion=today_ar() + timedelta(days=1))
    hoy = insert_cheque(caja_id, monto="20.00", fecha_liquidacion=today_ar())

    early = await _liquidar(client, secretaria_headers, caja_id, manana)
    on_time = await _liquidar(client, secretaria_headers, caja_id, hoy)

    assert early.status_code == 409
    assert "fecha de liquidación" in early.json()["detail"]
    assert get_movimiento(manana).fecha_liquidado is None
    assert on_time.status_code == 200
    saldo = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=secretaria_headers)
    assert saldo.json()["saldo_ars"] == "20.00"
