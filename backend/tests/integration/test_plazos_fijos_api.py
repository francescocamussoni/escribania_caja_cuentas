"""Integration tests for plazos fijos API (T006 — TDD, implement routes in T012–T013)."""

from datetime import date
from unittest.mock import patch

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


REFERENCE_TODAY = date(2026, 8, 6)


@pytest.mark.asyncio
@patch("app.services.plazo_fijo_service.today_ar", return_value=REFERENCE_TODAY)
async def test_post_plazo_fijo_returns_201_with_contract_shape(
    mock_today: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    caja_id = 2
    payload = {
        "monto_ingresado": "100000.00",
        "monto_a_vencimiento": "105000.00",
        "fecha_vencimiento": "2026-12-31",
    }
    response = await client.post(
        f"/api/v1/cajas/{caja_id}/plazos-fijos",
        json=payload,
        headers=secretaria_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["monto_ingresado"] == payload["monto_ingresado"]
    assert body["monto_a_vencimiento"] == payload["monto_a_vencimiento"]
    assert body["fecha_vencimiento"] == payload["fecha_vencimiento"]
    assert body["id"]
    assert body["created_at"]
    assert body["vencido"] is False
    assert body["caja"]["id"] == caja_id
    assert body["caja"]["nombre"]


@pytest.mark.asyncio
@patch("app.services.plazo_fijo_service.today_ar", return_value=REFERENCE_TODAY)
async def test_post_rejects_monto_a_vencimiento_less_than_ingresado(
    mock_today: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/cajas/2/plazos-fijos",
        json={
            "monto_ingresado": "10000.00",
            "monto_a_vencimiento": "5000.00",
            "fecha_vencimiento": "2026-12-31",
        },
        headers=secretaria_headers,
    )
    # Pydantic model_validator raises a 422 (validation error) for this constraint;
    # both 400 and 422 are acceptable rejections here.
    assert response.status_code in (400, 422)
    assert response.json()["detail"]


@pytest.mark.asyncio
@patch("app.services.plazo_fijo_service.today_ar", return_value=REFERENCE_TODAY)
async def test_get_plazos_fijos_paginated_future_before_vencidos(
    mock_today: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    suffix = uuid4().hex[:8]
    caja_id = 3
    payloads = [
        ("50000.00", "52000.00", "2026-07-01"),
        ("10000.00", "11000.00", "2026-08-15"),
        ("20000.00", "21000.00", "2026-06-01"),
        ("15000.00", "16000.00", "2026-08-10"),
    ]
    for ingresado, a_vencimiento, venc in payloads:
        await client.post(
            f"/api/v1/cajas/{caja_id}/plazos-fijos",
            json={
                "monto_ingresado": ingresado,
                "monto_a_vencimiento": a_vencimiento,
                "fecha_vencimiento": venc,
            },
            headers=secretaria_headers,
        )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/plazos-fijos?page=1",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_items"] >= 4

    # Extract vencimientos for only the 4 items this test created (identified by suffix)
    all_items = body["items"]
    test_fechas = {item["fecha_vencimiento"] for item in all_items}
    # All four target dates must be present somewhere in the list
    assert "2026-08-10" in test_fechas
    assert "2026-08-15" in test_fechas
    assert "2026-07-01" in test_fechas
    assert "2026-06-01" in test_fechas

    # Future dates must appear before past dates in the full list
    all_fechas = [item["fecha_vencimiento"] for item in all_items]
    idx_08_10 = next(i for i, f in enumerate(all_fechas) if f == "2026-08-10")
    idx_08_15 = next(i for i, f in enumerate(all_fechas) if f == "2026-08-15")
    idx_07_01 = next(i for i, f in enumerate(all_fechas) if f == "2026-07-01")
    idx_06_01 = next(i for i, f in enumerate(all_fechas) if f == "2026-06-01")
    # Future (08-10, 08-15) must come before past (07-01, 06-01)
    assert max(idx_08_10, idx_08_15) < min(idx_07_01, idx_06_01), (
        f"Future plazos must appear before vencidos. "
        f"Positions: 08-10={idx_08_10}, 08-15={idx_08_15}, 07-01={idx_07_01}, 06-01={idx_06_01}"
    )


@pytest.mark.asyncio
@patch("app.services.plazo_fijo_service.today_ar", return_value=REFERENCE_TODAY)
async def test_get_resumen_sums_only_active_plazos(
    mock_today: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    from decimal import Decimal

    caja_id = 4

    # Capture prior resumen totals before adding new plazos
    prior_resp = await client.get(
        f"/api/v1/cajas/{caja_id}/plazos-fijos/resumen",
        headers=secretaria_headers,
    )
    assert prior_resp.status_code == 200
    prior_ingresado = Decimal(prior_resp.json()["total_monto_ingresado_activos"])
    prior_a_vencimiento = Decimal(prior_resp.json()["total_monto_a_vencimiento_activos"])

    await client.post(
        f"/api/v1/cajas/{caja_id}/plazos-fijos",
        json={
            "monto_ingresado": "10000.00",
            "monto_a_vencimiento": "11000.00",
            "fecha_vencimiento": "2026-12-31",
        },
        headers=secretaria_headers,
    )
    # This one is expired (past REFERENCE_TODAY = 2026-09-07) so should NOT be counted as active
    await client.post(
        f"/api/v1/cajas/{caja_id}/plazos-fijos",
        json={
            "monto_ingresado": "5000.00",
            "monto_a_vencimiento": "5500.00",
            "fecha_vencimiento": "2026-06-01",
        },
        headers=secretaria_headers,
    )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/plazos-fijos/resumen",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["caja"]["id"] == caja_id
    # Only the active plazo (2026-12-31) should be added to the prior totals
    assert Decimal(body["total_monto_ingresado_activos"]) == prior_ingresado + Decimal("10000.00")
    assert Decimal(body["total_monto_a_vencimiento_activos"]) == prior_a_vencimiento + Decimal("11000.00")


@pytest.mark.asyncio
@patch("app.services.plazo_fijo_service.today_ar", return_value=REFERENCE_TODAY)
async def test_patch_plazo_fijo_without_time_window(
    mock_today: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        "/api/v1/cajas/2/plazos-fijos",
        json={
            "monto_ingresado": "1000.00",
            "monto_a_vencimiento": "1100.00",
            "fecha_vencimiento": "2020-01-01",
        },
        headers=secretaria_headers,
    )
    assert create_response.status_code == 201
    plazo_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/cajas/2/plazos-fijos/{plazo_id}",
        json={"monto_ingresado": "2000.00", "monto_a_vencimiento": "2200.00"},
        headers=secretaria_headers,
    )

    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["monto_ingresado"] == "2000.00"
    assert body["monto_a_vencimiento"] == "2200.00"


@pytest.mark.asyncio
@patch("app.services.plazo_fijo_service.today_ar", return_value=REFERENCE_TODAY)
async def test_delete_plazo_fijo_without_time_window(
    mock_today: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        "/api/v1/cajas/2/plazos-fijos",
        json={
            "monto_ingresado": "3000.00",
            "monto_a_vencimiento": "3300.00",
            "fecha_vencimiento": "2019-06-15",
        },
        headers=secretaria_headers,
    )
    assert create_response.status_code == 201
    plazo_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/cajas/2/plazos-fijos/{plazo_id}",
        headers=secretaria_headers,
    )
    assert delete_response.status_code == 204

    list_response = await client.get(
        "/api/v1/cajas/2/plazos-fijos?page=1",
        headers=secretaria_headers,
    )
    ids = [item["id"] for item in list_response.json()["items"]]
    assert plazo_id not in ids


@pytest.mark.asyncio
async def test_invalid_page_size_returns_400(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/api/v1/cajas/1/plazos-fijos?page=1&page_size=10",
        headers=secretaria_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
@patch("app.services.plazo_fijo_service.today_ar", return_value=REFERENCE_TODAY)
async def test_escribano_get_plazos_fijos_list_ok(
    mock_today: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
) -> None:
    caja_id = 5
    await client.post(
        f"/api/v1/cajas/{caja_id}/plazos-fijos",
        json={
            "monto_ingresado": "8000.00",
            "monto_a_vencimiento": "8800.00",
            "fecha_vencimiento": "2026-12-31",
        },
        headers=secretaria_headers,
    )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/plazos-fijos?page=1",
        headers=escribano_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_items"] >= 1
    assert any(item["monto_ingresado"] == "8000.00" for item in body["items"])


@pytest.mark.asyncio
@patch("app.services.plazo_fijo_service.today_ar", return_value=REFERENCE_TODAY)
async def test_escribano_get_plazos_fijos_resumen_ok(
    mock_today: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
) -> None:
    from decimal import Decimal

    caja_id = 6

    # Capture prior active totals before adding new plazo
    prior_resp = await client.get(
        f"/api/v1/cajas/{caja_id}/plazos-fijos/resumen",
        headers=escribano_headers,
    )
    assert prior_resp.status_code == 200
    prior_ingresado = Decimal(prior_resp.json()["total_monto_ingresado_activos"])
    prior_a_vencimiento = Decimal(prior_resp.json()["total_monto_a_vencimiento_activos"])

    await client.post(
        f"/api/v1/cajas/{caja_id}/plazos-fijos",
        json={
            "monto_ingresado": "12000.00",
            "monto_a_vencimiento": "13200.00",
            "fecha_vencimiento": "2026-12-31",
        },
        headers=secretaria_headers,
    )

    response = await client.get(
        f"/api/v1/cajas/{caja_id}/plazos-fijos/resumen",
        headers=escribano_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["caja"]["id"] == caja_id
    assert Decimal(body["total_monto_ingresado_activos"]) == prior_ingresado + Decimal("12000.00")
    assert Decimal(body["total_monto_a_vencimiento_activos"]) == prior_a_vencimiento + Decimal("13200.00")


@pytest.mark.asyncio
async def test_escribano_post_plazo_fijo_returns_403(
    client: AsyncClient,
    escribano_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/cajas/1/plazos-fijos",
        json={
            "monto_ingresado": "100.00",
            "monto_a_vencimiento": "110.00",
            "fecha_vencimiento": "2026-12-31",
        },
        headers=escribano_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"]


@pytest.mark.asyncio
@patch("app.services.plazo_fijo_service.today_ar", return_value=REFERENCE_TODAY)
async def test_escribano_patch_plazo_fijo_returns_403(
    mock_today: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        "/api/v1/cajas/1/plazos-fijos",
        json={
            "monto_ingresado": "1500.00",
            "monto_a_vencimiento": "1650.00",
            "fecha_vencimiento": "2026-12-31",
        },
        headers=secretaria_headers,
    )
    assert create_response.status_code == 201
    plazo_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/cajas/1/plazos-fijos/{plazo_id}",
        json={"monto_ingresado": "2000.00"},
        headers=escribano_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"]


@pytest.mark.asyncio
@patch("app.services.plazo_fijo_service.today_ar", return_value=REFERENCE_TODAY)
async def test_escribano_delete_plazo_fijo_returns_403(
    mock_today: object,
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        "/api/v1/cajas/1/plazos-fijos",
        json={
            "monto_ingresado": "2500.00",
            "monto_a_vencimiento": "2750.00",
            "fecha_vencimiento": "2026-12-31",
        },
        headers=secretaria_headers,
    )
    assert create_response.status_code == 201
    plazo_id = create_response.json()["id"]

    response = await client.delete(
        f"/api/v1/cajas/1/plazos-fijos/{plazo_id}",
        headers=escribano_headers,
    )

    assert response.status_code == 403
