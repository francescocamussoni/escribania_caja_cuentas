"""
T026 — TDD: vistas derivadas tras un endose (feature 011, US3).

Un cheque endosado ya está liquidado: no debe figurar como pendiente en ninguna vista, y
ambos movimientos (cheque en origen, movimiento inverso en destino) impactan los saldos.
Cada test usa cajas nuevas y vacías.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.dates import today_ar
from app.db.session import SessionLocal
from app.services.informe_service import InformeService

from .cheque_helpers import insert_cheque


@pytest.fixture
async def otra_caja(client: AsyncClient, secretaria_headers: dict[str, str]) -> dict:
    response = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": f"Vistas {uuid4().hex[:12]}"},
        headers=secretaria_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _endosar(client, headers, caja_id: int, cheque_id: int, destino_id: int) -> dict:
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos/{cheque_id}/endosar",
        json={"caja_destino_id": destino_id},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _ids(response) -> list[int]:
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


@pytest.mark.asyncio
async def test_endorsed_cheque_is_no_longer_pending_in_any_view(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    hoy = today_ar()
    apto = insert_cheque(caja_id, monto="100.00", fecha_liquidacion=hoy - timedelta(days=1))
    proximo = insert_cheque(caja_id, monto="50.00", fecha_liquidacion=hoy + timedelta(days=1))
    futuro = insert_cheque(caja_id, monto="25.00", fecha_liquidacion=date(2099, 12, 1))

    # Sanity: the three are pending and visible before the endose.
    pendientes = await client.get(
        f"/api/v1/cajas/{caja_id}/cheques-pendientes", headers=secretaria_headers
    )
    assert sorted(_ids(pendientes)) == sorted([apto, proximo, futuro])

    await _endosar(client, secretaria_headers, caja_id, apto, otra_caja["id"])
    await _endosar(client, secretaria_headers, caja_id, futuro, otra_caja["id"])

    pendientes = await client.get(
        f"/api/v1/cajas/{caja_id}/cheques-pendientes", headers=secretaria_headers
    )
    assert _ids(pendientes) == [proximo]

    # Sección Cheques (todas las cajas): ni "aptos" ni "proximos" listan los endosados.
    for categoria in ("aptos", "proximos"):
        response = await client.get(
            "/api/v1/cheques", params={"categoria": categoria}, headers=secretaria_headers
        )
        ids = _ids(response)
        assert apto not in ids and futuro not in ids
    proximos = await client.get(
        "/api/v1/cheques", params={"categoria": "proximos"}, headers=secretaria_headers
    )
    assert proximo in _ids(proximos)

    # Saldo a futuro: solo queda el cheque que sigue pendiente (50.00 sobre saldo 100+25).
    saldo_futuro = await client.get(
        f"/api/v1/cajas/{caja_id}/saldo-futuro", headers=secretaria_headers
    )
    assert saldo_futuro.status_code == 200
    ars = next(m for m in saldo_futuro.json()["monedas"] if m["moneda"] == "ARS")
    assert ars["saldo_actual"] == "125.00"
    assert [fila["cheques"] for fila in ars["filas"]] == [1]
    assert ars["filas"][0]["saldo_proyectado"] == "175.00"

    # Saldo proyectado a una fecha futura: tampoco cuenta los endosados como pendientes.
    proyectado = await client.get(
        f"/api/v1/cajas/{caja_id}/saldo-proyectado",
        params={"fecha": date(2100, 1, 1).isoformat()},
        headers=secretaria_headers,
    )
    assert proyectado.status_code == 200, proyectado.text
    ars_proy = next(m for m in proyectado.json()["monedas"] if m["moneda"] == "ARS")
    assert Decimal(ars_proy["saldo_proyectado"]) == Decimal("175.00")


@pytest.mark.asyncio
async def test_both_movements_show_in_their_historial_and_saldos_net_to_zero(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    cheque_id = insert_cheque(fresh_caja["id"], tipo="entrada", monto="500.00")
    body = await _endosar(client, secretaria_headers, fresh_caja["id"], cheque_id, otra_caja["id"])
    destino_id = body["movimiento_destino"]["id"]

    origen = await client.get(
        f"/api/v1/cajas/{fresh_caja['id']}/movimientos", headers=secretaria_headers
    )
    destino = await client.get(
        f"/api/v1/cajas/{otra_caja['id']}/movimientos", headers=secretaria_headers
    )
    assert _ids(origen) == [cheque_id]
    assert _ids(destino) == [destino_id]

    async def saldo(caja_id: int) -> Decimal:
        response = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=secretaria_headers)
        return Decimal(response.json()["saldo_ars"])

    assert await saldo(fresh_caja["id"]) == Decimal("500.00")
    assert await saldo(otra_caja["id"]) == Decimal("-500.00")

    # Saldo general: ambas cajas figuran con su saldo y la suma de las dos es 0.
    general = await client.get("/api/v1/cajas/saldo-general", headers=secretaria_headers)
    assert general.status_code == 200
    por_caja = {
        item["caja"]["id"]: Decimal(item["saldo_ars"]) for item in general.json()["cajas"]
    }
    assert por_caja[fresh_caja["id"]] + por_caja[otra_caja["id"]] == Decimal("0")


@pytest.mark.asyncio
async def test_informe_service_lists_both_movements_and_no_pending_cheque(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, otra_caja: dict
) -> None:
    pendiente = insert_cheque(fresh_caja["id"], tipo="salida", monto="10.00")
    endosado = insert_cheque(fresh_caja["id"], tipo="entrada", monto="500.00")
    body = await _endosar(client, secretaria_headers, fresh_caja["id"], endosado, otra_caja["id"])
    destino_id = body["movimiento_destino"]["id"]

    hoy = today_ar()
    date_from, date_to = hoy - timedelta(days=1), hoy + timedelta(days=1)
    with SessionLocal() as session:
        service = InformeService(session)
        origen_movs = service.fetch_movimientos_informe(
            caja_id=fresh_caja["id"], date_from=date_from, date_to=date_to
        )
        destino_movs = service.fetch_movimientos_informe(
            caja_id=otra_caja["id"], date_from=date_from, date_to=date_to
        )
        pendientes, total = service.fetch_cheques_pendientes(fresh_caja["id"])

    assert [m.id for m in origen_movs] == [endosado]
    assert [m.id for m in destino_movs] == [destino_id]
    assert [m.id for m in pendientes] == [pendiente]
    assert total == 1
