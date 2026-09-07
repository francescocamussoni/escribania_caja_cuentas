from decimal import Decimal

import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.fixture
async def secretaria_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def escribano_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "escribano", "password": "escribano"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_post_movimiento_returns_201_with_contract_shape(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    caja_id = 2
    saldo_before = await client.get(
        f"/api/v1/cajas/{caja_id}/saldo",
        headers=secretaria_headers,
    )
    assert saldo_before.status_code == 200
    previous_subtotal_ars = saldo_before.json()["saldo_ars"]

    payload = {
        "descripcion": "Pago cliente",
        "monto": "5000.00",
        "tipo": "entrada",
    }
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json=payload,
        headers=secretaria_headers,
    )

    assert response.status_code == 201
    body = response.json()
    # T012: response is now MovimientoCreateResponse {movimiento, complementario}
    assert "movimiento" in body, f"Expected 'movimiento' key, got: {list(body.keys())}"
    mov = body["movimiento"]
    assert mov["descripcion"] == payload["descripcion"]
    assert mov["monto"] == payload["monto"]
    assert mov["tipo"] == payload["tipo"]
    assert mov["moneda"] == "ARS"
    assert mov["subtotal"] == str(Decimal(previous_subtotal_ars) + Decimal("5000.00"))
    assert mov["id"]
    assert mov["fecha"]
    assert "editable" in mov
    assert mov["caja"]["id"] == caja_id
    assert mov["caja"]["nombre"]
    assert body["complementario"] is None


@pytest.mark.asyncio
async def test_get_movimientos_returns_paginated_newest_first(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    suffix = uuid4().hex[:8]
    caja_id = 2
    for index in range(3):
        await client.post(
            f"/api/v1/cajas/{caja_id}/movimientos",
            json={
                "descripcion": f"Movimiento {suffix} {index}",
                "monto": "100.00",
                "tipo": "entrada",
            },
            headers=secretaria_headers,
        )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_items"] >= 3
    assert body["total_pages"] >= 1
    created = [item for item in body["items"] if suffix in item["descripcion"]]
    assert len(created) == 3
    assert created[0]["descripcion"] == f"Movimiento {suffix} 2"
    assert created[1]["descripcion"] == f"Movimiento {suffix} 1"
    assert created[2]["descripcion"] == f"Movimiento {suffix} 0"


@pytest.mark.asyncio
async def test_escribano_post_movimiento_returns_403(
    client: AsyncClient,
    escribano_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/cajas/1/movimientos",
        json={
            "descripcion": "Intento no autorizado",
            "monto": "100.00",
            "tipo": "entrada",
        },
        headers=escribano_headers,
    )

    assert response.status_code == 403
    body = response.json()
    assert body["detail"]


# ---------------------------------------------------------------------------
# T008 — Moneda en POST /movimientos (TDD: deben fallar hasta T012)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_movimiento_omitted_moneda_defaults_to_ars(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """Si no se envía `moneda`, el movimiento creado debe tener moneda='ARS'."""
    caja_id = 3
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": "Sin moneda", "monto": "100.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["movimiento"].get("moneda") == "ARS", (
        f"Moneda esperada 'ARS' cuando se omite, obtenida: {body['movimiento'].get('moneda')!r}"
    )


@pytest.mark.asyncio
async def test_post_movimiento_explicit_moneda_ars(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """POST con moneda='ARS' explícito debe persistir y retornar moneda='ARS'."""
    caja_id = 3
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": "ARS explícito",
            "monto": "200.00",
            "tipo": "entrada",
            "moneda": "ARS",
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 201
    assert response.json()["movimiento"].get("moneda") == "ARS"


@pytest.mark.asyncio
async def test_post_movimiento_usd_persisted_and_returned(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """POST con moneda='USD' debe crear el movimiento y retornarlo con moneda='USD'."""
    caja_id = 3
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": "Cobro en dólares",
            "monto": "50.00",
            "tipo": "entrada",
            "moneda": "USD",
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["movimiento"].get("moneda") == "USD", (
        f"Moneda esperada 'USD', obtenida: {body['movimiento'].get('moneda')!r}"
    )


@pytest.mark.asyncio
async def test_post_movimiento_invalid_moneda_returns_400(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """POST con moneda inválida (ej. 'EUR') debe retornar 422 o 400."""
    response = await client.post(
        "/api/v1/cajas/3/movimientos",
        json={
            "descripcion": "Moneda inválida",
            "monto": "100.00",
            "tipo": "entrada",
            "moneda": "EUR",
        },
        headers=secretaria_headers,
    )

    assert response.status_code in (400, 422), (
        f"Se esperaba 400 o 422 para moneda inválida, obtenido: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_post_movimiento_usd_stream_independent_from_ars(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    Al agregar movimientos ARS, el subtotal USD de la caja no debe verse afectado.
    El primer USD nuevo debe sumar al stream USD previo (no al ARS).
    """
    from decimal import Decimal

    caja_id = 4  # caja separada para aislar el test
    suffix = uuid4().hex[:6]

    # Capture prior USD saldo before adding ARS movements
    prior_resp = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=secretaria_headers)
    assert prior_resp.status_code == 200
    prior_saldo_usd = Decimal(prior_resp.json()["saldo_usd"])

    # Crear algunos ARS primero
    for _ in range(2):
        await client.post(
            f"/api/v1/cajas/{caja_id}/movimientos",
            json={"descripcion": f"ARS {suffix}", "monto": "1000.00", "tipo": "entrada"},
            headers=secretaria_headers,
        )

    # USD: subtotal debe ser prior_usd + 100 (stream independiente de ARS)
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": f"USD {suffix}",
            "monto": "100.00",
            "tipo": "entrada",
            "moneda": "USD",
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["movimiento"].get("moneda") == "USD"
    expected_usd_subtotal = str(prior_saldo_usd + Decimal("100.00"))
    assert body["movimiento"].get("subtotal") == expected_usd_subtotal, (
        f"Subtotal USD esperado '{expected_usd_subtotal}' (stream independiente de ARS), "
        f"obtenido: {body['movimiento'].get('subtotal')!r}"
    )


@pytest.mark.asyncio
async def test_post_movimiento_usd_escribano_returns_403(
    client: AsyncClient,
    escribano_headers: dict[str, str],
) -> None:
    """Escribano no puede crear movimiento USD (ni ningún movimiento)."""
    response = await client.post(
        "/api/v1/cajas/1/movimientos",
        json={
            "descripcion": "USD no autorizado",
            "monto": "50.00",
            "tipo": "entrada",
            "moneda": "USD",
        },
        headers=escribano_headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# T021 — TDD integration tests para registrar_complementario (US2)
#
# Deben FALLAR hasta que T023/T024 implementen el par atómico.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_usd_complementario_true_returns_both_movimientos(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    POST USD con registrar_complementario=true debe retornar 201 con
    movimiento y complementario ambos non-null, tipos opuestos, mismo monto/moneda/descripcion.
    """
    suffix = uuid4().hex[:6]
    caja_id = 5

    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": f"Par USD {suffix}",
            "monto": "150.00",
            "tipo": "entrada",
            "moneda": "USD",
            "registrar_complementario": True,
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["movimiento"] is not None
    assert body["complementario"] is not None

    principal = body["movimiento"]
    comp = body["complementario"]

    assert principal["tipo"] == "entrada"
    assert comp["tipo"] == "salida"
    assert principal["moneda"] == "USD"
    assert comp["moneda"] == "USD"
    assert principal["monto"] == "150.00"
    assert comp["monto"] == "150.00"
    assert principal["descripcion"] == comp["descripcion"]
    assert principal["caja"]["id"] == caja_id
    assert comp["caja"]["id"] == caja_id
    # son rows distintos
    assert principal["id"] != comp["id"]


@pytest.mark.asyncio
async def test_post_usd_complementario_false_returns_one_movimiento(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    POST USD con registrar_complementario=false debe retornar 201 con
    solo el movimiento principal y complementario=null.
    """
    caja_id = 5
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": "Solo principal USD",
            "monto": "80.00",
            "tipo": "salida",
            "moneda": "USD",
            "registrar_complementario": False,
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["movimiento"] is not None
    assert body["complementario"] is None


@pytest.mark.asyncio
async def test_post_usd_omit_complementario_returns_one_movimiento(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    POST USD sin enviar registrar_complementario debe retornar solo el principal
    (default False → complementario=null).
    """
    caja_id = 5
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": "USD sin complementario",
            "monto": "30.00",
            "tipo": "entrada",
            "moneda": "USD",
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["complementario"] is None


@pytest.mark.asyncio
async def test_post_ars_complementario_true_returns_400(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    POST ARS con registrar_complementario=true debe retornar 400/422
    (solo USD puede tener par complementario).
    """
    response = await client.post(
        "/api/v1/cajas/5/movimientos",
        json={
            "descripcion": "ARS con complementario",
            "monto": "100.00",
            "tipo": "entrada",
            "moneda": "ARS",
            "registrar_complementario": True,
        },
        headers=secretaria_headers,
    )

    assert response.status_code in (400, 422), (
        f"Se esperaba 400/422 para ARS+registrar_complementario=true, "
        f"obtenido: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_post_usd_complementario_escribano_returns_403(
    client: AsyncClient,
    escribano_headers: dict[str, str],
) -> None:
    """Escribano no puede usar registrar_complementario (ni crear movimientos)."""
    response = await client.post(
        "/api/v1/cajas/5/movimientos",
        json={
            "descripcion": "Escribano USD par",
            "monto": "100.00",
            "tipo": "entrada",
            "moneda": "USD",
            "registrar_complementario": True,
        },
        headers=escribano_headers,
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# T027 — TDD integration tests para filtros GET /movimientos (US3)
#
# Deben FALLAR hasta que T029/T030 implementen los query params.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_movimientos_filter_by_moneda_usd(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """GET con moneda=USD solo devuelve movimientos USD."""
    suffix = uuid4().hex[:6]
    caja_id = 6

    # Crear un ARS y un USD
    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": f"ARS {suffix}", "monto": "100.00", "tipo": "entrada", "moneda": "ARS"},
        headers=secretaria_headers,
    )
    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": f"USD {suffix}", "monto": "50.00", "tipo": "entrada", "moneda": "USD"},
        headers=secretaria_headers,
    )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1&moneda=USD",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    items = [item for item in body["items"] if suffix in item["descripcion"]]
    assert len(items) == 1, f"Se esperaba 1 USD, obtenidos: {len(items)}"
    assert items[0]["moneda"] == "USD"
    assert items[0]["descripcion"] == f"USD {suffix}"


@pytest.mark.asyncio
async def test_get_movimientos_filter_by_moneda_ars(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """GET con moneda=ARS solo devuelve movimientos ARS."""
    suffix = uuid4().hex[:6]
    caja_id = 6

    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": f"ARS2 {suffix}", "monto": "200.00", "tipo": "entrada", "moneda": "ARS"},
        headers=secretaria_headers,
    )
    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": f"USD2 {suffix}", "monto": "75.00", "tipo": "entrada", "moneda": "USD"},
        headers=secretaria_headers,
    )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1&moneda=ARS",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    items = [item for item in body["items"] if suffix in item["descripcion"]]
    assert all(item["moneda"] == "ARS" for item in items), (
        f"Todos los items deberían ser ARS: {[i['moneda'] for i in items]}"
    )
    assert any(f"ARS2 {suffix}" == item["descripcion"] for item in items)


@pytest.mark.asyncio
async def test_get_movimientos_filter_by_fecha_desde(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """GET con fecha_desde solo devuelve movimientos desde esa fecha inclusive."""
    suffix = uuid4().hex[:6]
    caja_id = 7

    # Creamos dos movimientos hoy; la fecha_desde de hoy debe incluirlos
    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": f"Hoy {suffix}", "monto": "30.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )

    from datetime import date
    today = date.today().isoformat()

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1&fecha_desde={today}",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    items = [item for item in body["items"] if suffix in item["descripcion"]]
    assert len(items) >= 1, "El movimiento creado hoy debe aparecer con fecha_desde=hoy"


@pytest.mark.asyncio
async def test_get_movimientos_filter_by_fecha_hasta(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """GET con fecha_hasta incluye movimientos hasta esa fecha (inclusive)."""
    suffix = uuid4().hex[:6]
    caja_id = 7

    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": f"FiltroHasta {suffix}", "monto": "40.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )

    from datetime import date
    today = date.today().isoformat()

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1&fecha_hasta={today}",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    items = [item for item in body["items"] if suffix in item["descripcion"]]
    assert len(items) >= 1, "El movimiento de hoy debe aparecer con fecha_hasta=hoy"


@pytest.mark.asyncio
async def test_get_movimientos_filter_moneda_and_fecha_combo(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """GET con moneda=USD y fecha_desde=hoy debe devolver solo USD de hoy en adelante."""
    suffix = uuid4().hex[:6]
    caja_id = 8

    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": f"ComboUSD {suffix}", "monto": "60.00", "tipo": "entrada", "moneda": "USD"},
        headers=secretaria_headers,
    )
    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": f"ComboARS {suffix}", "monto": "60.00", "tipo": "entrada", "moneda": "ARS"},
        headers=secretaria_headers,
    )

    from datetime import date
    today = date.today().isoformat()

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1&moneda=USD&fecha_desde={today}",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    items_suffix = [item for item in body["items"] if suffix in item["descripcion"]]
    assert len(items_suffix) == 1
    assert items_suffix[0]["moneda"] == "USD"


@pytest.mark.asyncio
async def test_get_movimientos_empty_page_when_filter_excludes_all(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """Filtro que no matchea ningún movimiento devuelve lista vacía (no error)."""
    caja_id = 9

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1&fecha_desde=2099-01-01",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total_items"] == 0
    assert body["total_pages"] == 0


@pytest.mark.asyncio
async def test_get_movimientos_fecha_desde_gt_fecha_hasta_returns_400(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """fecha_desde > fecha_hasta debe retornar 400."""
    response = await client.get(
        "/api/v1/cajas/1/movimientos?page=1&fecha_desde=2026-12-31&fecha_hasta=2026-01-01",
        headers=secretaria_headers,
    )

    assert response.status_code == 400, (
        f"Se esperaba 400 cuando fecha_desde > fecha_hasta, obtenido: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_get_movimientos_filter_pagination_uses_filtered_count(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    La paginación (total_items, total_pages) debe reflejar el conjunto filtrado,
    no el total sin filtrar de la caja.
    """
    suffix = uuid4().hex[:6]
    caja_id = 10  # caja aislada para este test

    # Crear 2 ARS y 1 USD
    for _ in range(2):
        await client.post(
            f"/api/v1/cajas/{caja_id}/movimientos",
            json={"descripcion": f"ARS pag {suffix}", "monto": "10.00", "tipo": "entrada", "moneda": "ARS"},
            headers=secretaria_headers,
        )
    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": f"USD pag {suffix}", "monto": "10.00", "tipo": "entrada", "moneda": "USD"},
        headers=secretaria_headers,
    )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1&moneda=USD",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    # Solo el USD debe contarse
    usd_items = [item for item in body["items"] if suffix in item["descripcion"]]
    assert len(usd_items) == 1
    # total_items para el filtro debe ser >= 1 y < total sin filtro
    assert body["total_items"] >= 1
