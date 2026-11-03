"""
T054 — TDD: GET /api/v1/cajas/{id}/saldo-futuro (feature 010, US4).

Obligatorio por constitución: saldos/subtotales y RBAC. Cada test usa una caja nueva.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.dates import today_ar

from .cheque_helpers import insert_cheque

URL = "/api/v1/cajas/{caja_id}/saldo-futuro"


async def _saldo_futuro(client: AsyncClient, headers: dict, caja_id: int) -> dict:
    response = await client.get(URL.format(caja_id=caja_id), headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


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
async def test_spec_example_cumulative_projection(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    d1, d2 = date(2099, 11, 5), date(2099, 11, 20)
    await _common(client, secretaria_headers, caja_id, "entrada", "1000.00")
    insert_cheque(caja_id, tipo="entrada", monto="500.00", fecha_liquidacion=d1)
    insert_cheque(caja_id, tipo="salida", monto="200.00", fecha_liquidacion=d2)

    body = await _saldo_futuro(client, secretaria_headers, caja_id)

    ars = _moneda(body, "ARS")
    assert ars["saldo_actual"] == "1000.00"
    assert ars["filas"] == [
        {
            "fecha_liquidacion": "2099-11-05",
            "vencido": False,
            "cheques": 1,
            "efecto_neto": "500.00",
            "saldo_proyectado": "1500.00",
            "detalle": [
                {
                    "descripcion": "cheque de prueba",
                    "instrumento": "cheque",
                    "tipo": "entrada",
                    "monto": "500.00",
                }
            ],
        },
        {
            "fecha_liquidacion": "2099-11-20",
            "vencido": False,
            "cheques": 1,
            "efecto_neto": "-200.00",
            "saldo_proyectado": "1300.00",
            "detalle": [
                {
                    "descripcion": "cheque de prueba",
                    "instrumento": "cheque",
                    "tipo": "salida",
                    "monto": "200.00",
                }
            ],
        },
    ]
    assert body["caja"]["id"] == caja_id
    assert body["fecha_calculo"] == today_ar().isoformat()


@pytest.mark.asyncio
async def test_groups_same_date_in_one_row(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    fecha = date(2099, 12, 1)
    insert_cheque(caja_id, tipo="entrada", monto="300.00", fecha_liquidacion=fecha)
    insert_cheque(caja_id, tipo="salida", monto="100.00", fecha_liquidacion=fecha)

    body = await _saldo_futuro(client, secretaria_headers, caja_id)

    filas = _moneda(body, "ARS")["filas"]
    assert len(filas) == 1
    assert filas[0]["cheques"] == 2
    assert filas[0]["efecto_neto"] == "200.00"
    assert filas[0]["saldo_proyectado"] == "200.00"


@pytest.mark.asyncio
async def test_overdue_cheques_are_included_and_flagged(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    insert_cheque(caja_id, tipo="entrada", monto="40.00", fecha_liquidacion=today_ar())
    insert_cheque(
        caja_id, tipo="entrada", monto="60.00", fecha_liquidacion=today_ar() + timedelta(days=30)
    )

    body = await _saldo_futuro(client, secretaria_headers, caja_id)

    filas = _moneda(body, "ARS")["filas"]
    assert [f["vencido"] for f in filas] == [True, False]
    assert [f["saldo_proyectado"] for f in filas] == ["40.00", "100.00"]


@pytest.mark.asyncio
async def test_liquidated_cheques_are_excluded_and_absorbed_into_saldo_actual(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    insert_cheque(
        caja_id,
        tipo="entrada",
        monto="70.00",
        fecha_liquidacion=date(2099, 1, 1),
        fecha_liquidado=datetime.now(timezone.utc),
        subtotal="70.00",
    )
    insert_cheque(caja_id, tipo="entrada", monto="30.00", fecha_liquidacion=date(2099, 2, 1))

    body = await _saldo_futuro(client, secretaria_headers, caja_id)

    ars = _moneda(body, "ARS")
    assert ars["saldo_actual"] == "70.00"
    assert [f["saldo_proyectado"] for f in ars["filas"]] == ["100.00"]


@pytest.mark.asyncio
async def test_ars_and_usd_are_independent(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    insert_cheque(caja_id, tipo="entrada", monto="500.00", moneda="ARS", fecha_liquidacion=date(2099, 3, 1))
    insert_cheque(caja_id, tipo="salida", monto="20.00", moneda="USD", fecha_liquidacion=date(2099, 3, 1))

    body = await _saldo_futuro(client, secretaria_headers, caja_id)

    assert [m["moneda"] for m in body["monedas"]] == ["ARS", "USD"]
    assert _moneda(body, "ARS")["filas"][0]["saldo_proyectado"] == "500.00"
    assert _moneda(body, "USD")["filas"][0]["saldo_proyectado"] == "-20.00"


@pytest.mark.asyncio
async def test_without_pending_cheques_only_todays_balance(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _common(client, secretaria_headers, caja_id, "entrada", "15.00")

    body = await _saldo_futuro(client, secretaria_headers, caja_id)

    assert _moneda(body, "ARS") == {"moneda": "ARS", "saldo_actual": "15.00", "filas": []}
    assert _moneda(body, "USD") == {"moneda": "USD", "saldo_actual": "0.00", "filas": []}


@pytest.mark.asyncio
async def test_saldo_actual_matches_the_saldo_endpoint(
    client: AsyncClient, secretaria_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _common(client, secretaria_headers, caja_id, "entrada", "80.00")
    await _common(client, secretaria_headers, caja_id, "salida", "5.50")
    insert_cheque(caja_id, monto="999.00", fecha_liquidacion=date(2099, 5, 1))

    futuro = await _saldo_futuro(client, secretaria_headers, caja_id)
    saldo = (
        await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=secretaria_headers)
    ).json()

    assert _moneda(futuro, "ARS")["saldo_actual"] == saldo["saldo_ars"] == "74.50"
    assert Decimal(_moneda(futuro, "USD")["saldo_actual"]) == Decimal(saldo["saldo_usd"])


@pytest.mark.asyncio
async def test_escribano_can_read(
    client: AsyncClient, escribano_headers: dict, fresh_caja: dict
) -> None:
    response = await client.get(URL.format(caja_id=fresh_caja["id"]), headers=escribano_headers)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unknown_caja_is_404(client: AsyncClient, secretaria_headers: dict) -> None:
    response = await client.get(URL.format(caja_id=99999999), headers=secretaria_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_without_token_is_401(client: AsyncClient, fresh_caja: dict) -> None:
    response = await client.get(URL.format(caja_id=fresh_caja["id"]))

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rows_include_the_description_of_each_cheque(
    client: AsyncClient, escribano_headers: dict, fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    d1 = date(2099, 11, 5)
    insert_cheque(caja_id, descripcion="Honorarios Pérez", monto="300.00", fecha_liquidacion=d1)
    insert_cheque(
        caja_id,
        descripcion="Pago sellado",
        tipo="salida",
        monto="100.00",
        instrumento="echeque",
        fecha_liquidacion=d1,
    )

    body = await _saldo_futuro(client, escribano_headers, caja_id)

    fila = _moneda(body, "ARS")["filas"][0]
    assert fila["cheques"] == 2
    assert fila["detalle"] == [
        {
            "descripcion": "Honorarios Pérez",
            "instrumento": "cheque",
            "tipo": "entrada",
            "monto": "300.00",
        },
        {
            "descripcion": "Pago sellado",
            "instrumento": "echeque",
            "tipo": "salida",
            "monto": "100.00",
        },
    ]
