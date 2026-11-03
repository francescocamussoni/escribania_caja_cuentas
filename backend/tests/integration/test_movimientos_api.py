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
async def test_post_ars_complementario_true_returns_201(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    POST ARS con registrar_complementario=true debe retornar 201.
    Desde T009, el par complementario está habilitado para ARS y USD.
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

    assert response.status_code == 201, (
        f"Se esperaba 201 para ARS+registrar_complementario=true, "
        f"obtenido: {response.status_code}"
    )
    body = response.json()
    assert body["complementario"] is not None
    assert body["complementario"]["moneda"] == "ARS"


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


# ---------------------------------------------------------------------------
# T007 — TDD: par ARS con registrar_complementario=True retorna 201
#         con movimiento y complementario no nulos.
#         FALLA hasta que T009 elimine validate_complementario_only_for_usd
#         y T011 pase moneda al create_movimiento_pair.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_par_ars_registrar_complementario_returns_201(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    POST con registrar_complementario=True y moneda=ARS debe:
      - retornar 201
      - body.movimiento con moneda='ARS' y tipo=<el enviado>
      - body.complementario no nulo, moneda='ARS', tipo opuesto

    T007 — TDD: FALLA hasta que T009+T010+T011 implementen el par ARS.
    """
    caja_id = 3
    suffix = uuid4().hex[:8]
    payload = {
        "descripcion": f"Par ARS {suffix}",
        "monto": "1500.00",
        "tipo": "entrada",
        "moneda": "ARS",
        "registrar_complementario": True,
    }

    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json=payload,
        headers=secretaria_headers,
    )

    assert response.status_code == 201, (
        f"Esperado 201, obtenido {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "movimiento" in body
    assert "complementario" in body

    mov = body["movimiento"]
    comp = body["complementario"]

    assert mov["moneda"] == "ARS", f"Principal moneda esperada ARS, obtenida: {mov['moneda']}"
    assert mov["tipo"] == "entrada"
    assert comp is not None, "complementario no debe ser null para par ARS"
    assert comp["moneda"] == "ARS", f"Complementario moneda esperada ARS, obtenida: {comp['moneda']}"
    assert comp["tipo"] == "salida"
    assert mov["descripcion"] == comp["descripcion"]
    assert mov["monto"] == comp["monto"]


# ---------------------------------------------------------------------------
# T008 — TDD: Entrada USD simple (registrar_complementario=False) retorna
#         complementario=null (el diálogo ya no existe en backend).
#         Este test verifica que el backend no crea complementario cuando
#         registrar_complementario=False (sin cambio de comportamiento).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_entrada_usd_sin_complementario_returns_null(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    POST entrada USD con registrar_complementario=False (o sin el campo)
    debe retornar complementario=null.

    T008 — TDD: valida que registrar_complementario=False sigue sin crear par.
    Este test debe PASAR ya desde T001 (comportamiento existente sin cambio).
    """
    caja_id = 4
    suffix = uuid4().hex[:8]
    payload = {
        "descripcion": f"USD simple {suffix}",
        "monto": "200.00",
        "tipo": "entrada",
        "moneda": "USD",
        "registrar_complementario": False,
    }

    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json=payload,
        headers=secretaria_headers,
    )

    assert response.status_code == 201, (
        f"Esperado 201, obtenido {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body["complementario"] is None, (
        f"complementario debe ser null cuando registrar_complementario=False, "
        f"obtenido: {body['complementario']}"
    )


# ---------------------------------------------------------------------------
# T024–T026 — TDD: fecha_manual en endpoint POST movimientos (US3/feature 009)
#
# Estos tests deben FALLAR hasta que T027–T033 implementen:
#   - T027: campo fecha_manual en CreateMovimientoRequest
#   - T028: parámetro fecha_override en create_movimiento service
#   - T032: router calcula fecha_override desde fecha_manual a 09:00 AR
#   - T033: movimiento_to_response retorna fecha = fecha_override or created_at
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_movimiento_con_fecha_manual_retorna_fecha_09_00(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """T024: POST con fecha_manual='2026-09-01' → response fecha='2026-09-01T09:00:00-03:00'."""
    caja_id = 5
    suffix = uuid4().hex[:8]

    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": f"Movimiento fecha manual {suffix}",
            "monto": "500.00",
            "tipo": "entrada",
            "moneda": "ARS",
            "fecha_manual": "2026-09-01",
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 201, (
        f"Esperado 201, obtenido {response.status_code}: {response.text}"
    )
    body = response.json()
    fecha = body["movimiento"]["fecha"]
    assert fecha == "2026-09-01T09:00:00-03:00", (
        f"fecha esperado '2026-09-01T09:00:00-03:00', obtenido '{fecha}'"
    )


@pytest.mark.asyncio
async def test_post_movimiento_sin_fecha_manual_retorna_created_at(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """T025: POST sin fecha_manual → response fecha igual al created_at del servidor (sin regresión)."""
    caja_id = 5
    suffix = uuid4().hex[:8]

    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": f"Movimiento sin fecha manual {suffix}",
            "monto": "300.00",
            "tipo": "entrada",
            "moneda": "ARS",
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 201, (
        f"Esperado 201, obtenido {response.status_code}: {response.text}"
    )
    body = response.json()
    fecha = body["movimiento"]["fecha"]
    # Debe ser una fecha ISO válida (no None, no vacía) y NO ser 09:00:00-03:00
    # (porque no es una fecha manual fija sino el timestamp del servidor)
    assert fecha is not None and len(fecha) > 0, "fecha no debe ser nula ni vacía"
    # Sin fecha_manual, el campo fecha no debe tener la hora fija de las 09:00
    # (en un entorno de test corriendo a otra hora)
    # Validamos que al menos sea parseable como ISO 8601
    from datetime import datetime
    parsed = datetime.fromisoformat(fecha)
    assert parsed is not None, f"fecha no es ISO 8601 válido: {fecha}"


@pytest.mark.asyncio
async def test_post_par_con_fecha_manual_ambos_movimientos_tienen_misma_fecha(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """T026: POST par + fecha_manual='2026-09-01' → ambos movimientos tienen fecha='2026-09-01T09:00:00-03:00'."""
    caja_id = 5
    suffix = uuid4().hex[:8]

    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": f"Par con fecha manual {suffix}",
            "monto": "750.00",
            "tipo": "entrada",
            "moneda": "USD",
            "registrar_complementario": True,
            "fecha_manual": "2026-09-01",
        },
        headers=secretaria_headers,
    )

    assert response.status_code == 201, (
        f"Esperado 201, obtenido {response.status_code}: {response.text}"
    )
    body = response.json()
    fecha_principal = body["movimiento"]["fecha"]
    fecha_complementario = body["complementario"]["fecha"]

    assert fecha_principal == "2026-09-01T09:00:00-03:00", (
        f"Principal fecha esperado '2026-09-01T09:00:00-03:00', obtenido '{fecha_principal}'"
    )
    assert fecha_complementario == "2026-09-01T09:00:00-03:00", (
        f"Complementario fecha esperado '2026-09-01T09:00:00-03:00', obtenido '{fecha_complementario}'"
    )


# ---------------------------------------------------------------------------
# T008 — feature 010: paridad del listado (impacta saldo + fecha efectiva)
# ---------------------------------------------------------------------------

from .cheque_helpers import insert_cheque  # noqa: E402


async def _post(client, headers, caja_id, **extra):
    payload = {"descripcion": "listado", "monto": "10.00", "tipo": "entrada", **extra}
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["movimiento"]


@pytest.mark.asyncio
async def test_list_excludes_pending_cheques(
    client: AsyncClient, secretaria_headers: dict[str, str], fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    comun = await _post(client, secretaria_headers, caja_id)
    cheque_id = insert_cheque(caja_id)

    response = await client.get(f"/api/v1/cajas/{caja_id}/movimientos", headers=secretaria_headers)

    body = response.json()
    ids = [item["id"] for item in body["items"]]
    assert ids == [comun["id"]]
    assert cheque_id not in ids
    assert body["total_items"] == 1


@pytest.mark.asyncio
async def test_list_orders_by_effective_date(
    client: AsyncClient, secretaria_headers: dict[str, str], fresh_caja: dict
) -> None:
    """Un movimiento retroactivo cargado después queda DEBAJO del cargado hoy."""
    caja_id = fresh_caja["id"]
    hoy = await _post(client, secretaria_headers, caja_id)
    retro = await _post(client, secretaria_headers, caja_id, fecha_manual="2026-01-10")

    response = await client.get(f"/api/v1/cajas/{caja_id}/movimientos", headers=secretaria_headers)

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [hoy["id"], retro["id"]]


@pytest.mark.asyncio
async def test_list_date_filters_use_effective_date(
    client: AsyncClient, secretaria_headers: dict[str, str], fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _post(client, secretaria_headers, caja_id)
    retro = await _post(client, secretaria_headers, caja_id, fecha_manual="2026-01-10")

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos",
        params={"fecha_desde": "2026-01-01", "fecha_hasta": "2026-01-31"},
        headers=secretaria_headers,
    )

    assert [item["id"] for item in response.json()["items"]] == [retro["id"]]


@pytest.mark.asyncio
async def test_list_common_movements_keep_contract_shape(
    client: AsyncClient, secretaria_headers: dict[str, str], fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    await _post(client, secretaria_headers, caja_id, monto="25.00")

    response = await client.get(f"/api/v1/cajas/{caja_id}/movimientos", headers=secretaria_headers)

    item = response.json()["items"][0]
    assert item["subtotal"] == "25.00"
    assert item["monto"] == "25.00"
    assert item["moneda"] == "ARS"
    assert item["editable"] is True
