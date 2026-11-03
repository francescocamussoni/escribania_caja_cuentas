from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.catalog.cajas import CAJAS_CATALOG


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
async def test_escribano_can_get_saldo_and_movimientos_for_all_cajas(
    client: AsyncClient,
    escribano_headers: dict[str, str],
    secretaria_headers: dict[str, str],
) -> None:
    await client.post(
        "/api/v1/cajas/1/movimientos",
        json={
            "descripcion": "Movimiento de prueba consulta",
            "monto": "250.00",
            "tipo": "entrada",
        },
        headers=secretaria_headers,
    )

    cajas_response = await client.get("/api/v1/cajas", headers=escribano_headers)
    assert cajas_response.status_code == 200
    cajas = cajas_response.json()
    # Integration tests share the DB within the session; other tests may add cajas,
    # so we assert at least the 15 catalog cajas are present.
    assert len(cajas) >= len(CAJAS_CATALOG)

    for caja in cajas:
        saldo_response = await client.get(
            f"/api/v1/cajas/{caja['id']}/saldo",
            headers=escribano_headers,
        )
        assert saldo_response.status_code == 200
        saldo_body = saldo_response.json()
        assert saldo_body["caja"]["id"] == caja["id"]
        assert "saldo_ars" in saldo_body

        movimientos_response = await client.get(
            f"/api/v1/cajas/{caja['id']}/movimientos?page=1",
            headers=escribano_headers,
        )
        assert movimientos_response.status_code == 200
        movimientos_body = movimientos_response.json()
        assert movimientos_body["page"] == 1
        assert movimientos_body["page_size"] == 20
        assert "items" in movimientos_body


@pytest.mark.asyncio
async def test_secretaria_can_get_saldo_and_movimientos_for_all_cajas(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    cajas_response = await client.get("/api/v1/cajas", headers=secretaria_headers)
    assert cajas_response.status_code == 200
    cajas = cajas_response.json()
    # Integration tests share the DB within the session; other tests may add cajas,
    # so we assert at least the 15 catalog cajas are present.
    assert len(cajas) >= len(CAJAS_CATALOG)

    for caja in cajas:
        saldo_response = await client.get(
            f"/api/v1/cajas/{caja['id']}/saldo",
            headers=secretaria_headers,
        )
        assert saldo_response.status_code == 200

        movimientos_response = await client.get(
            f"/api/v1/cajas/{caja['id']}/movimientos?page=1",
            headers=secretaria_headers,
        )
        assert movimientos_response.status_code == 200


# ---------------------------------------------------------------------------
# T079 — feature 010: matriz RBAC de todos los endpoints nuevos/cambiados
#
#   escritura (crear / editar / eliminar / liquidar) → Secretaria sí, Escribano 403
#   lectura (saldo-futuro, cheques-pendientes, /cheques, informe) → ambos roles 200
#   sin token → 401 en todos
# ---------------------------------------------------------------------------

from .cheque_helpers import get_movimiento, insert_cheque  # noqa: E402

_CHEQUE_PAYLOAD = {
    "descripcion": "Cheque RBAC",
    "monto": "10.00",
    "tipo": "entrada",
    "instrumento": "cheque",
    "fecha_liquidacion": "2999-01-01",
}


async def _request(client: AsyncClient, method: str, url: str, headers: dict | None, body=None):
    kwargs: dict = {"headers": headers} if headers else {}
    if body is not None:
        kwargs["json"] = body
    return await client.request(method, url, **kwargs)


def _write_cases(caja_id: int) -> list[tuple[str, str, str, dict | None, int]]:
    """(name, method, url, body, secretaria success status) — one pending cheque per case."""
    base = f"/api/v1/cajas/{caja_id}/movimientos"
    cheque_patch = insert_cheque(caja_id)
    cheque_delete = insert_cheque(caja_id)
    cheque_liquidar = insert_cheque(caja_id, fecha_liquidacion=date(2020, 1, 1))
    return [
        ("create cheque", "POST", base, _CHEQUE_PAYLOAD, 201),
        ("update cheque", "PATCH", f"{base}/{cheque_patch}", {"instrumento": "echeque"}, 200),
        ("delete cheque", "DELETE", f"{base}/{cheque_delete}", None, 204),
        ("liquidar cheque", "POST", f"{base}/{cheque_liquidar}/liquidar", None, 200),
    ]


@pytest.mark.asyncio
async def test_cheque_write_endpoints_are_secretaria_only(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
    fresh_caja: dict,
) -> None:
    for name, method, url, body, ok_status in _write_cases(fresh_caja["id"]):
        no_token = await _request(client, method, url, None, body)
        assert no_token.status_code == 401, f"{name}: sin token"

        forbidden = await _request(client, method, url, escribano_headers, body)
        assert forbidden.status_code == 403, f"{name}: escribano"

    # Escribano's rejected attempts changed nothing: all three cheques are still pending.
    caja_id = fresh_caja["id"]
    pendientes = await client.get(
        f"/api/v1/cajas/{caja_id}/cheques-pendientes", headers=escribano_headers
    )
    assert pendientes.json()["total_items"] == 3
    assert all(i["instrumento"] == "cheque" for i in pendientes.json()["items"])

    # The Secretaria can perform every one of them.
    ok_caja = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": f"RBAC cheques {uuid4().hex[:8]}"},
        headers=secretaria_headers,
    )
    assert ok_caja.status_code == 201, ok_caja.text
    for name, method, url, body, ok_status in _write_cases(ok_caja.json()["id"]):
        response = await _request(client, method, url, secretaria_headers, body)
        assert response.status_code == ok_status, f"{name}: secretaria"


@pytest.mark.asyncio
async def test_escribano_cannot_liquidar_even_with_a_valid_cheque(
    client: AsyncClient, escribano_headers: dict[str, str], fresh_caja: dict
) -> None:
    caja_id = fresh_caja["id"]
    cheque_id = insert_cheque(caja_id)

    response = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos/{cheque_id}/liquidar", headers=escribano_headers
    )

    assert response.status_code == 403
    assert get_movimiento(cheque_id).fecha_liquidado is None


def _read_cases(caja_id: int) -> list[tuple[str, str, str, dict | None]]:
    return [
        ("saldo futuro", "GET", f"/api/v1/cajas/{caja_id}/saldo-futuro", None),
        ("cheques pendientes", "GET", f"/api/v1/cajas/{caja_id}/cheques-pendientes", None),
        ("seccion aptos", "GET", "/api/v1/cheques?categoria=aptos", None),
        ("seccion proximos", "GET", "/api/v1/cheques?categoria=proximos", None),
        (
            "informe caja",
            "POST",
            "/api/v1/informes/pdf",
            {
                "tipo": "CAJA",
                "caja_id": 1,
                "modo": "PERIODO",
                "fecha_inicio": "2026-01-01",
                "fecha_fin": "2026-01-31",
            },
        ),
    ]


@pytest.mark.asyncio
async def test_cheque_read_endpoints_are_available_to_both_roles(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
    fresh_caja: dict,
) -> None:
    insert_cheque(fresh_caja["id"])

    for name, method, url, body in _read_cases(fresh_caja["id"]):
        for role, headers in (("secretaria", secretaria_headers), ("escribano", escribano_headers)):
            response = await _request(client, method, url, headers, body)
            assert response.status_code == 200, f"{name}: {role}"

        no_token = await _request(client, method, url, None, body)
        assert no_token.status_code == 401, f"{name}: sin token"


@pytest.mark.asyncio
async def test_cheque_read_endpoints_return_404_for_unknown_caja(
    client: AsyncClient, escribano_headers: dict[str, str]
) -> None:
    for suffix in ("saldo-futuro", "cheques-pendientes"):
        response = await client.get(
            f"/api/v1/cajas/99999999/{suffix}", headers=escribano_headers
        )
        assert response.status_code == 404, suffix
