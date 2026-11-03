"""T083 — recorrido del quickstart (feature 010) automatizado a nivel API con ambos roles.

Reproduce los pasos de la verificación manual de `quickstart.md` (Secretaria, Escribano y
casos de borde) contra la API real, sin atajos en la base de datos.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.dates import today_ar
from app.db.session import SessionLocal
from app.models.movimiento import Movimiento


def _make_due(movimiento_id: int) -> None:
    """The API only accepts future fechas de liquidación: move it to the past directly."""
    with SessionLocal() as session:
        mov = session.get(Movimiento, movimiento_id)
        mov.fecha_liquidacion = today_ar() - timedelta(days=1)
        session.commit()


async def _saldo(client: AsyncClient, headers: dict, caja_id: int) -> Decimal:
    response = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=headers)
    assert response.status_code == 200
    return Decimal(response.json()["saldo_ars"])


async def _crear(client: AsyncClient, headers: dict, caja_id: int, **payload) -> dict:
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["movimiento"]


@pytest.mark.asyncio
async def test_quickstart_secretaria_and_escribano_flow(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
    fresh_caja: dict,
) -> None:
    caja_id = fresh_caja["id"]
    d1 = (today_ar() + timedelta(days=10)).isoformat()
    d2 = (today_ar() + timedelta(days=20)).isoformat()

    # 1-2. Saldo conocido con un movimiento común.
    base = await _crear(
        client, secretaria_headers, caja_id,
        descripcion="Saldo inicial", monto="1000.00", tipo="entrada",
    )
    assert base["instrumento"] == "ninguno" and base["subtotal"] == "1000.00"
    assert await _saldo(client, secretaria_headers, caja_id) == Decimal("1000.00")

    # 4. Fecha de liquidación vacía / hoy / pasada → rechazo; no se crea nada.
    for bad in (None, today_ar().isoformat(), (today_ar() - timedelta(days=1)).isoformat()):
        payload = {
            "descripcion": "Cheque inválido", "monto": "5.00", "tipo": "entrada",
            "instrumento": "cheque",
        }
        if bad is not None:
            payload["fecha_liquidacion"] = bad
        response = await client.post(
            f"/api/v1/cajas/{caja_id}/movimientos", json=payload, headers=secretaria_headers
        )
        assert response.status_code == 422, bad

    # 5-6. Cheque entrada 500 (D1) y echeque salida 200 (D2): no impactan el saldo.
    entrada = await _crear(
        client, secretaria_headers, caja_id,
        descripcion="Cheque entrada", monto="500.00", tipo="entrada",
        instrumento="cheque", fecha_liquidacion=d1,
    )
    salida = await _crear(
        client, secretaria_headers, caja_id,
        descripcion="Cheque salida", monto="200.00", tipo="salida",
        instrumento="echeque", fecha_liquidacion=d2,
    )
    assert entrada["estado"] == "pendiente" and entrada["subtotal"] is None
    assert await _saldo(client, secretaria_headers, caja_id) == Decimal("1000.00")

    pendientes = await client.get(
        f"/api/v1/cajas/{caja_id}/cheques-pendientes", headers=secretaria_headers
    )
    assert {i["id"] for i in pendientes.json()["items"]} == {entrada["id"], salida["id"]}

    # 7. Saldo a futuro: Hoy 1000 · D1 1500 · D2 1300 (ambos roles ven lo mismo).
    for headers in (secretaria_headers, escribano_headers):
        futuro = await client.get(f"/api/v1/cajas/{caja_id}/saldo-futuro", headers=headers)
        assert futuro.status_code == 200
        ars = next(m for m in futuro.json()["monedas"] if m["moneda"] == "ARS")
        assert Decimal(ars["saldo_actual"]) == Decimal("1000.00")
        assert [(f["fecha_liquidacion"], Decimal(f["saldo_proyectado"])) for f in ars["filas"]] == [
            (d1, Decimal("1500.00")),
            (d2, Decimal("1300.00")),
        ]

    # 8. Editar un cheque pendiente no cambia el saldo; cheque ↔ echeque OK, "ninguno" no.
    edit = await client.patch(
        f"/api/v1/cajas/{caja_id}/movimientos/{entrada['id']}",
        json={"instrumento": "echeque", "monto": "600.00"},
        headers=secretaria_headers,
    )
    assert edit.status_code == 200 and edit.json()["instrumento"] == "echeque"
    assert await _saldo(client, secretaria_headers, caja_id) == Decimal("1000.00")
    invalid = await client.patch(
        f"/api/v1/cajas/{caja_id}/movimientos/{entrada['id']}",
        json={"instrumento": "ninguno"},
        headers=secretaria_headers,
    )
    assert invalid.status_code == 422

    # Escribano: solo lectura; los intentos de escritura reciben 403 y nada cambia.
    for method, url, body in (
        ("POST", f"/api/v1/cajas/{caja_id}/movimientos/{entrada['id']}/liquidar", None),
        ("PATCH", f"/api/v1/cajas/{caja_id}/movimientos/{entrada['id']}", {"monto": "1.00"}),
        ("DELETE", f"/api/v1/cajas/{caja_id}/movimientos/{entrada['id']}", None),
    ):
        kwargs = {"json": body} if body else {}
        response = await client.request(method, url, headers=escribano_headers, **kwargs)
        assert response.status_code == 403, method
    assert await _saldo(client, escribano_headers, caja_id) == Decimal("1000.00")

    # Antes de su fecha de liquidación el cheque no se puede liquidar (regla de negocio).
    early = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos/{entrada['id']}/liquidar",
        headers=secretaria_headers,
    )
    assert early.status_code == 409
    assert await _saldo(client, secretaria_headers, caja_id) == Decimal("1000.00")

    # 9. Llegada la fecha, liquidar el cheque de entrada (600): saldo 1600, pasa al historial.
    _make_due(entrada["id"])
    liquidado = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos/{entrada['id']}/liquidar",
        headers=secretaria_headers,
    )
    assert liquidado.status_code == 200
    body = liquidado.json()
    assert body["estado"] == "liquidado" and body["subtotal"] == "1600.00"
    assert body["liquidable"] is False
    assert await _saldo(client, secretaria_headers, caja_id) == Decimal("1600.00")

    # Borde: segunda liquidación → 409 y el saldo no se duplica.
    again = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos/{entrada['id']}/liquidar",
        headers=secretaria_headers,
    )
    assert again.status_code == 409
    assert await _saldo(client, secretaria_headers, caja_id) == Decimal("1600.00")

    # El historial incluye el cheque liquidado y excluye el pendiente.
    historial = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1", headers=escribano_headers
    )
    ids = {i["id"] for i in historial.json()["items"]}
    assert entrada["id"] in ids and salida["id"] not in ids and base["id"] in ids

    # 10. Sección Cheques disponible para ambos roles.
    for headers in (secretaria_headers, escribano_headers):
        for categoria in ("aptos", "proximos"):
            response = await client.get(f"/api/v1/cheques?categoria={categoria}", headers=headers)
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_quickstart_cajas_adicionales_are_independent(
    client: AsyncClient, secretaria_headers: dict[str, str], fresh_caja: dict
) -> None:
    otra = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": f"Quickstart {fresh_caja['nombre'][-8:]}"},
        headers=secretaria_headers,
    )
    assert otra.status_code == 201
    fecha = (today_ar() + timedelta(days=5)).isoformat()

    cheques = []
    for caja_id in (fresh_caja["id"], otra.json()["id"]):
        cheques.append(
            await _crear(
                client, secretaria_headers, caja_id,
                descripcion="Cheque adicional", monto="50.00", tipo="entrada",
                instrumento="cheque", fecha_liquidacion=fecha,
            )
        )

    for caja_id, cheque in zip((fresh_caja["id"], otra.json()["id"]), cheques):
        pendientes = await client.get(
            f"/api/v1/cajas/{caja_id}/cheques-pendientes", headers=secretaria_headers
        )
        assert [i["id"] for i in pendientes.json()["items"]] == [cheque["id"]]
        assert await _saldo(client, secretaria_headers, caja_id) == Decimal("0.00")

    # Liquidar uno (ya vencido) no toca la otra caja.
    _make_due(cheques[0]["id"])
    await client.post(
        f"/api/v1/cajas/{fresh_caja['id']}/movimientos/{cheques[0]['id']}/liquidar",
        headers=secretaria_headers,
    )
    assert await _saldo(client, secretaria_headers, fresh_caja["id"]) == Decimal("50.00")
    assert await _saldo(client, secretaria_headers, otra.json()["id"]) == Decimal("0.00")
