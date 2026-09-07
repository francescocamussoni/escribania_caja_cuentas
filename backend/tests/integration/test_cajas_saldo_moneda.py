"""
T009 — TDD: tests de integración para el endpoint GET /api/v1/cajas/{id}/saldo.

Regla de negocio (spec US1 / data-model.md / OpenAPI contract):
  - La respuesta debe incluir `saldo_ars` y `saldo_usd` como campos separados.
  - NO debe incluir `saldo_actual` mezclado.
  - Los saldos son independientes: ARS no afecta USD y viceversa.
  - Si no hay movimientos de una moneda, el saldo de esa moneda es "0.00".

Estos tests deben FALLAR hasta que T013 actualice CajaSaldoResponse y el endpoint.
"""

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


# ---------------------------------------------------------------------------
# T009 — saldo dual (saldo_ars + saldo_usd)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_saldo_response_has_saldo_ars_field(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """GET /saldo debe retornar el campo `saldo_ars`."""
    response = await client.get(
        "/api/v1/cajas/1/saldo",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert "saldo_ars" in body, (
        f"Respuesta de /saldo no contiene 'saldo_ars'. Campos: {list(body.keys())}"
    )


@pytest.mark.asyncio
async def test_saldo_response_has_saldo_usd_field(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """GET /saldo debe retornar el campo `saldo_usd`."""
    response = await client.get(
        "/api/v1/cajas/1/saldo",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert "saldo_usd" in body, (
        f"Respuesta de /saldo no contiene 'saldo_usd'. Campos: {list(body.keys())}"
    )


@pytest.mark.asyncio
async def test_saldo_response_does_not_mix_currencies(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    GET /saldo NO debe retornar `saldo_actual` mezclado.
    El contrato breaking change (OpenAPI 008) elimina saldo_actual.
    """
    response = await client.get(
        "/api/v1/cajas/1/saldo",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert "saldo_actual" not in body, (
        f"'saldo_actual' no debe estar en la respuesta (campo deprecated). "
        f"Campos presentes: {list(body.keys())}"
    )


@pytest.mark.asyncio
async def test_saldo_usd_starts_at_zero_when_no_usd_movements(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    Si solo se agregan movimientos ARS, `saldo_usd` no cambia respecto al estado previo.
    Cuando la caja no tenía USD previos, saldo_usd debe quedar en "0.00".
    """
    suffix = uuid4().hex[:6]
    caja_id = 5

    # Capture prior saldo_usd before adding ARS movements
    prior_resp = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=secretaria_headers)
    assert prior_resp.status_code == 200
    prior_saldo_usd = prior_resp.json().get("saldo_usd")

    # Crear solo movimientos ARS
    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": f"ARS only {suffix}",
            "monto": "300.00",
            "tipo": "entrada",
            "moneda": "ARS",
        },
        headers=secretaria_headers,
    )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/saldo",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    # Adding ARS movements must NOT change saldo_usd
    assert body.get("saldo_usd") == prior_saldo_usd, (
        f"saldo_usd no debe cambiar al agregar solo movimientos ARS. "
        f"Antes: {prior_saldo_usd!r}, Después: {body.get('saldo_usd')!r}"
    )


@pytest.mark.asyncio
async def test_saldo_ars_starts_at_zero_when_no_ars_movements(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    Si solo se agregan movimientos USD, `saldo_ars` no cambia respecto al estado previo.
    Cuando la caja no tenía ARS previos, saldo_ars debe quedar en "0.00".
    """
    suffix = uuid4().hex[:6]
    caja_id = 6

    # Capture prior saldo_ars before adding USD movements
    prior_resp = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=secretaria_headers)
    assert prior_resp.status_code == 200
    prior_saldo_ars = prior_resp.json().get("saldo_ars")

    # Crear solo movimientos USD
    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": f"USD only {suffix}",
            "monto": "150.00",
            "tipo": "entrada",
            "moneda": "USD",
        },
        headers=secretaria_headers,
    )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/saldo",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    # Adding USD movements must NOT change saldo_ars
    assert body.get("saldo_ars") == prior_saldo_ars, (
        f"saldo_ars no debe cambiar al agregar solo movimientos USD. "
        f"Antes: {prior_saldo_ars!r}, Después: {body.get('saldo_ars')!r}"
    )


@pytest.mark.asyncio
async def test_saldo_ars_and_usd_are_independent(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """
    Con movimientos de ambas monedas, saldo_ars y saldo_usd reflejan
    correctamente cada stream sin mezclarlos.
    """
    from decimal import Decimal

    suffix = uuid4().hex[:6]
    caja_id = 7

    # Capture prior saldos before adding this test's movements
    prior_resp = await client.get(f"/api/v1/cajas/{caja_id}/saldo", headers=secretaria_headers)
    assert prior_resp.status_code == 200
    prior_saldo_ars = Decimal(prior_resp.json()["saldo_ars"])
    prior_saldo_usd = Decimal(prior_resp.json()["saldo_usd"])

    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": f"ARS entrada {suffix}",
            "monto": "500.00",
            "tipo": "entrada",
            "moneda": "ARS",
        },
        headers=secretaria_headers,
    )
    await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={
            "descripcion": f"USD entrada {suffix}",
            "monto": "200.00",
            "tipo": "entrada",
            "moneda": "USD",
        },
        headers=secretaria_headers,
    )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/saldo",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    expected_ars = str(prior_saldo_ars + Decimal("500.00"))
    expected_usd = str(prior_saldo_usd + Decimal("200.00"))
    assert body.get("saldo_ars") == expected_ars, (
        f"saldo_ars esperado '{expected_ars}', obtenido: {body.get('saldo_ars')!r}"
    )
    assert body.get("saldo_usd") == expected_usd, (
        f"saldo_usd esperado '{expected_usd}', obtenido: {body.get('saldo_usd')!r}"
    )


@pytest.mark.asyncio
async def test_saldo_caja_sin_movimientos_returns_zero_for_both(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    """Caja sin movimientos retorna saldo_ars='0.00' y saldo_usd='0.00'."""
    # Caja 1 puede tener movimientos de tests anteriores; buscamos una caja
    # específica sin movimientos — la caja 10 (catalog) no tiene actividad
    response = await client.get(
        "/api/v1/cajas/10/saldo",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body.get("saldo_ars") is not None, "'saldo_ars' ausente en caja sin movimientos"
    assert body.get("saldo_usd") is not None, "'saldo_usd' ausente en caja sin movimientos"
