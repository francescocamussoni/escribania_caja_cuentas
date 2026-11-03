"""GET /api/v1/cajas/{id}/saldo-proyectado?fecha=... (Valor de caja total a una fecha).

Obligatorio por constitución: saldos y RBAC (solo Secretaria). Cada test usa una caja nueva.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.dates import today_ar

from .cheque_helpers import insert_cheque

URL = "/api/v1/cajas/{caja_id}/saldo-proyectado"


async def _get(client: AsyncClient, headers: dict | None, caja_id: int, fecha: date):
    kwargs = {"headers": headers} if headers else {}
    return await client.get(
        URL.format(caja_id=caja_id), params={"fecha": fecha.isoformat()}, **kwargs
    )


def _moneda(body: dict, moneda: str) -> dict:
    return next(m for m in body["monedas"] if m["moneda"] == moneda)


async def _common(client: AsyncClient, headers: dict, caja_id: int, tipo: str, monto: str):
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": "comun", "monto": monto, "tipo": tipo},
        headers=headers,
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_adds_pending_cheques_due_by_the_chosen_date(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    d1, d2 = today_ar() + timedelta(days=10), today_ar() + timedelta(days=20)
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00")
    insert_cheque(caja_id, tipo="entrada", monto="500.00", fecha_liquidacion=d1)
    insert_cheque(caja_id, tipo="salida", monto="200.00", fecha_liquidacion=d2)

    en_d1 = (await _get(client, secretaria_headers, caja_id, d1)).json()
    en_d2 = (await _get(client, secretaria_headers, caja_id, d2)).json()
    antes = (await _get(client, secretaria_headers, caja_id, today_ar() + timedelta(days=1))).json()

    assert _moneda(en_d1, "ARS") == {
        "moneda": "ARS", "saldo_actual": "1000.00", "efecto_cheques": "500.00",
        "saldo_proyectado": "1500.00", "cheques": 1,
    }
    assert _moneda(en_d2, "ARS")["saldo_proyectado"] == "1300.00"
    assert _moneda(en_d2, "ARS")["cheques"] == 2
    assert _moneda(antes, "ARS")["saldo_proyectado"] == "1000.00"
    assert en_d1["fecha"] == d1.isoformat() and en_d1["caja"]["id"] == caja_id


@pytest.mark.asyncio
async def test_overdue_pending_cheques_are_included_and_liquidated_ones_are_not_double_counted(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    insert_cheque(caja_id, monto="30.00", fecha_liquidacion=date(2020, 1, 1))  # vencido, pendiente
    insert_cheque(
        caja_id, monto="100.00", fecha_liquidacion=date(2020, 1, 1),
        fecha_liquidado=datetime.now(timezone.utc), subtotal="100.00",
    )  # liquidado: ya está en el saldo actual

    body = (await _get(client, secretaria_headers, caja_id, today_ar() + timedelta(days=5))).json()

    ars = _moneda(body, "ARS")
    assert ars["saldo_actual"] == "100.00"
    assert ars["efecto_cheques"] == "30.00"
    assert ars["saldo_proyectado"] == "130.00"
    assert ars["cheques"] == 1


@pytest.mark.asyncio
async def test_ars_and_usd_are_independent(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    fecha = today_ar() + timedelta(days=3)
    insert_cheque(caja_id, moneda="USD", monto="70.00", fecha_liquidacion=fecha)

    body = (await _get(client, secretaria_headers, caja_id, fecha)).json()

    assert _moneda(body, "USD")["saldo_proyectado"] == "70.00"
    assert _moneda(body, "ARS")["saldo_proyectado"] == "0.00"
    assert _moneda(body, "ARS")["cheques"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("delta", [0, -1, -400])
async def test_date_must_be_after_today(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict, delta: int
) -> None:
    response = await _get(
        client, secretaria_headers, fresh_caja["id"], today_ar() + timedelta(days=delta)
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_without_date_includes_every_pending_cheque(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00")
    insert_cheque(caja_id, monto="500.00", fecha_liquidacion=date(2040, 1, 1))
    insert_cheque(caja_id, tipo="salida", monto="100.00", fecha_liquidacion=date(2050, 1, 1))

    response = await client.get(URL.format(caja_id=caja_id), headers=secretaria_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["fecha"] is None
    assert _moneda(body, "ARS")["saldo_proyectado"] == "1400.00"
    assert _moneda(body, "ARS")["cheques"] == 2


@pytest.mark.asyncio
async def test_list_has_running_valor_total_for_secretaria_only(
    client: AsyncClient, secretaria_headers: dict, escribano_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    hoy = today_ar()
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00")
    insert_cheque(caja_id, monto="500.00", descripcion="c1", fecha_liquidacion=hoy + timedelta(days=5))
    insert_cheque(caja_id, tipo="salida", monto="200.00", descripcion="c2",
                  fecha_liquidacion=hoy + timedelta(days=9))
    insert_cheque(caja_id, moneda="USD", monto="7.00", descripcion="usd",
                  fecha_liquidacion=hoy + timedelta(days=9))
    url = f"/api/v1/cajas/{caja_id}/movimientos"

    items = (await client.get(url, params={"incluir_pendientes": "true"},
                              headers=secretaria_headers)).json()["items"]
    por_desc = {i["descripcion"]: i for i in items}

    assert por_desc["comun"]["valor_total"] == "1000.00"
    assert por_desc["c1"]["valor_total"] == "1500.00"
    assert por_desc["c2"]["valor_total"] == "1300.00"
    assert por_desc["usd"]["valor_total"] == "7.00"

    for headers in (escribano_headers,):
        otros = (await client.get(url, params={"incluir_pendientes": "true"},
                                  headers=headers)).json()["items"]
        assert all(i["valor_total"] is None for i in otros)
    sin_flag = (await client.get(url, headers=secretaria_headers)).json()["items"]
    assert all(i["valor_total"] is None for i in sin_flag)


@pytest.mark.asyncio
async def test_missing_or_malformed_date_is_422(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    url = URL.format(caja_id=fresh_caja["id"])

    assert (
        await client.get(url, params={"fecha": "no-es-fecha"}, headers=secretaria_headers)
    ).status_code == 422


@pytest.mark.asyncio
async def test_unknown_caja_is_404(client: AsyncClient, secretaria_headers: dict) -> None:
    response = await _get(client, secretaria_headers, 99999999, today_ar() + timedelta(days=1))

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_escribano_is_forbidden(
    client: AsyncClient, escribano_headers: dict, fresh_caja: dict
) -> None:
    response = await _get(
        client, escribano_headers, fresh_caja["id"], today_ar() + timedelta(days=1)
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_without_token_is_401(client: AsyncClient, fresh_caja: dict) -> None:
    response = await _get(client, None, fresh_caja["id"], today_ar() + timedelta(days=1))

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_matches_the_saldo_futuro_table(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    d1, d2 = today_ar() + timedelta(days=4), today_ar() + timedelta(days=9)
    insert_cheque(caja_id, tipo="entrada", monto="500.00", fecha_liquidacion=d1)
    insert_cheque(caja_id, tipo="salida", monto="120.00", fecha_liquidacion=d2)

    futuro = (
        await client.get(f"/api/v1/cajas/{caja_id}/saldo-futuro", headers=secretaria_headers)
    ).json()
    filas = next(m for m in futuro["monedas"] if m["moneda"] == "ARS")["filas"]
    for fila in filas:
        body = (
            await _get(client, secretaria_headers, caja_id, date.fromisoformat(fila["fecha_liquidacion"]))
        ).json()
        assert _moneda(body, "ARS")["saldo_proyectado"] == fila["saldo_proyectado"]


@pytest.mark.asyncio
async def test_hasta_filter_uses_fecha_de_cobro_for_cheques_and_registro_for_the_rest(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    hoy = today_ar()
    await _common(client, secretaria_headers, caja_id, "entrada", "10.00")  # registrado hoy
    insert_cheque(caja_id, monto="500.00", descripcion="cobro-cercano",
                  fecha_liquidacion=hoy + timedelta(days=5))
    insert_cheque(caja_id, monto="700.00", descripcion="cobro-lejano",
                  fecha_liquidacion=hoy + timedelta(days=30))

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos",
        params={"fecha_hasta": (hoy + timedelta(days=10)).isoformat(), "incluir_pendientes": "true"},
        headers=secretaria_headers,
    )

    descripciones = {i["descripcion"] for i in response.json()["items"]}
    assert descripciones == {"comun", "cobro-cercano"}
