from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.usuario import Usuario


def _commit_user(*, rol: str) -> tuple[str, str]:
    prefix = "sec" if rol == "secretaria" else "esc"
    username = f"{prefix}_{uuid4().hex[:10]}"
    password = "TestPass12"
    db = SessionLocal()
    try:
        existing = db.scalar(select(Usuario).where(Usuario.username == username))
        if existing is None:
            db.add(
                Usuario(
                    username=username,
                    password_hash=hash_password(password),
                    rol=rol,
                )
            )
            db.commit()
    finally:
        db.close()
    return username, password


def _commit_secretaria() -> tuple[str, str]:
    return _commit_user(rol="secretaria")


@pytest.fixture
async def secretaria_headers(client: AsyncClient) -> dict[str, str]:
    username, password = _commit_secretaria()
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def escribano_headers(client: AsyncClient) -> dict[str, str]:
    username, password = _commit_user(rol="escribano")
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _unique_nombre(prefix: str) -> str:
    return f"{prefix} {uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_post_cajas_config_returns_201_activa(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    nombre = _unique_nombre("Caja Config")
    response = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": nombre},
        headers=secretaria_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["nombre"] == nombre
    assert body["estado"] == "activa"
    assert body["id"]
    assert body["slug"]


@pytest.mark.asyncio
async def test_post_cajas_config_duplicate_returns_400(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    nombre = _unique_nombre("Caja Dup")
    first = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": nombre},
        headers=secretaria_headers,
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": nombre.lower()},
        headers=secretaria_headers,
    )

    assert second.status_code == 400
    assert second.json()["detail"]


@pytest.mark.asyncio
async def test_post_cajas_config_without_token_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": _unique_nombre("Sin Auth")},
    )

    assert response.status_code == 401
    assert response.json()["detail"]


@pytest.mark.asyncio
async def test_post_cajas_archive_returns_200(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    created = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": _unique_nombre("Caja Archivar")},
        headers=secretaria_headers,
    )
    assert created.status_code == 201
    caja_id = created.json()["id"]

    response = await client.post(
        f"/api/v1/cajas/{caja_id}/archive",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == caja_id
    assert body["estado"] == "archivada"


@pytest.mark.asyncio
async def test_post_cajas_archive_is_idempotent(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    created = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": _unique_nombre("Caja Idemp")},
        headers=secretaria_headers,
    )
    caja_id = created.json()["id"]

    first = await client.post(
        f"/api/v1/cajas/{caja_id}/archive",
        headers=secretaria_headers,
    )
    second = await client.post(
        f"/api/v1/cajas/{caja_id}/archive",
        headers=secretaria_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["estado"] == "archivada"


@pytest.mark.asyncio
async def test_post_cajas_unarchive_returns_200(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    created = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": _unique_nombre("Caja Unarch")},
        headers=secretaria_headers,
    )
    caja_id = created.json()["id"]
    archived = await client.post(
        f"/api/v1/cajas/{caja_id}/archive",
        headers=secretaria_headers,
    )
    assert archived.status_code == 200

    response = await client.post(
        f"/api/v1/cajas/{caja_id}/unarchive",
        headers=secretaria_headers,
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "activa"

    operativas = await client.get("/api/v1/cajas", headers=secretaria_headers)
    nombres = {item["nombre"] for item in operativas.json()}
    assert created.json()["nombre"] in nombres


@pytest.mark.asyncio
async def test_post_cajas_unarchive_is_idempotent(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    created = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": _unique_nombre("Caja Unarch Idemp")},
        headers=secretaria_headers,
    )
    caja_id = created.json()["id"]

    first = await client.post(
        f"/api/v1/cajas/{caja_id}/unarchive",
        headers=secretaria_headers,
    )
    second = await client.post(
        f"/api/v1/cajas/{caja_id}/unarchive",
        headers=secretaria_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["estado"] == "activa"


@pytest.mark.asyncio
async def test_post_cajas_unarchive_unknown_returns_404(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/cajas/32767/unarchive",
        headers=secretaria_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"]


@pytest.mark.asyncio
async def test_post_cajas_archive_unknown_returns_404(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/cajas/32767/archive",
        headers=secretaria_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"]


@pytest.mark.asyncio
async def test_archive_keeps_movimientos_historial(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    created = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": _unique_nombre("Caja Hist")},
        headers=secretaria_headers,
    )
    assert created.status_code == 201
    caja_id = created.json()["id"]
    descripcion = f"Movimiento hist {uuid4().hex[:8]}"

    movimiento = await client.post(
        f"/api/v1/cajas/{caja_id}/movimientos",
        json={"descripcion": descripcion, "monto": "100.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )
    assert movimiento.status_code == 201

    archived = await client.post(
        f"/api/v1/cajas/{caja_id}/archive",
        headers=secretaria_headers,
    )
    assert archived.status_code == 200

    historial = await client.get(
        f"/api/v1/cajas/{caja_id}/movimientos?page=1",
        headers=secretaria_headers,
    )
    assert historial.status_code == 200
    items = historial.json()["items"]
    assert any(item["descripcion"] == descripcion for item in items)


@pytest.mark.asyncio
async def test_get_cajas_config_includes_activas_and_archivadas(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    activa_nombre = _unique_nombre("Cfg Activa")
    archivada_nombre = _unique_nombre("Cfg Archivada")

    activa = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": activa_nombre},
        headers=secretaria_headers,
    )
    archivada = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": archivada_nombre},
        headers=secretaria_headers,
    )
    assert activa.status_code == 201
    assert archivada.status_code == 201

    archive = await client.post(
        f"/api/v1/cajas/{archivada.json()['id']}/archive",
        headers=secretaria_headers,
    )
    assert archive.status_code == 200

    response = await client.get("/api/v1/cajas/config", headers=secretaria_headers)
    assert response.status_code == 200
    by_nombre = {item["nombre"]: item for item in response.json()}
    assert by_nombre[activa_nombre]["estado"] == "activa"
    assert by_nombre[archivada_nombre]["estado"] == "archivada"


@pytest.mark.asyncio
async def test_get_cajas_and_operativas_exclude_archivadas(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    activa_nombre = _unique_nombre("Op Activa")
    archivada_nombre = _unique_nombre("Op Archivada")

    activa = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": activa_nombre},
        headers=secretaria_headers,
    )
    archivada = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": archivada_nombre},
        headers=secretaria_headers,
    )
    assert activa.status_code == 201
    archivada_id = archivada.json()["id"]
    archive = await client.post(
        f"/api/v1/cajas/{archivada_id}/archive",
        headers=secretaria_headers,
    )
    assert archive.status_code == 200

    for path in ("/api/v1/cajas", "/api/v1/cajas/operativas"):
        response = await client.get(path, headers=secretaria_headers)
        assert response.status_code == 200
        nombres = {item["nombre"] for item in response.json()}
        assert activa_nombre in nombres
        assert archivada_nombre not in nombres
        assert all(item["estado"] == "activa" for item in response.json())

    saldo = await client.get(
        f"/api/v1/cajas/{archivada_id}/saldo",
        headers=secretaria_headers,
    )
    assert saldo.status_code == 200
    assert saldo.json()["caja"]["id"] == archivada_id


@pytest.mark.asyncio
async def test_escribano_cannot_create_or_archive_cajas(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
    escribano_headers: dict[str, str],
) -> None:
    created = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": _unique_nombre("Caja 403")},
        headers=secretaria_headers,
    )
    assert created.status_code == 201
    caja_id = created.json()["id"]

    create_forbidden = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": _unique_nombre("Escribano Alta")},
        headers=escribano_headers,
    )
    assert create_forbidden.status_code == 403
    assert create_forbidden.json()["detail"]

    archive_forbidden = await client.post(
        f"/api/v1/cajas/{caja_id}/archive",
        headers=escribano_headers,
    )
    assert archive_forbidden.status_code == 403
    assert archive_forbidden.json()["detail"]

    unarchive_forbidden = await client.post(
        f"/api/v1/cajas/{caja_id}/unarchive",
        headers=escribano_headers,
    )
    assert unarchive_forbidden.status_code == 403
    assert unarchive_forbidden.json()["detail"]

    config_forbidden = await client.get(
        "/api/v1/cajas/config",
        headers=escribano_headers,
    )
    assert config_forbidden.status_code == 403

    list_ok = await client.get("/api/v1/cajas", headers=escribano_headers)
    assert list_ok.status_code == 200
    assert isinstance(list_ok.json(), list)


@pytest.mark.asyncio
async def test_get_saldo_general_secretaria_sums_activas_only(
    client: AsyncClient,
    secretaria_headers: dict[str, str],
) -> None:
    before = await client.get(
        "/api/v1/cajas/saldo-general",
        headers=secretaria_headers,
    )
    assert before.status_code == 200
    before_count = before.json()["cajas_incluidas"]

    activa = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": _unique_nombre("Saldo Gen Activa")},
        headers=secretaria_headers,
    )
    archivada = await client.post(
        "/api/v1/cajas/config",
        json={"nombre": _unique_nombre("Saldo Gen Arch")},
        headers=secretaria_headers,
    )
    activa_id = activa.json()["id"]
    archivada_id = archivada.json()["id"]

    mov_a = await client.post(
        f"/api/v1/cajas/{activa_id}/movimientos",
        json={"descripcion": "entrada gen", "monto": "40.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )
    mov_arch = await client.post(
        f"/api/v1/cajas/{archivada_id}/movimientos",
        json={"descripcion": "entrada arch", "monto": "80.00", "tipo": "entrada"},
        headers=secretaria_headers,
    )
    assert mov_a.status_code == 201
    assert mov_arch.status_code == 201

    archive = await client.post(
        f"/api/v1/cajas/{archivada_id}/archive",
        headers=secretaria_headers,
    )
    assert archive.status_code == 200

    after = await client.get(
        "/api/v1/cajas/saldo-general",
        headers=secretaria_headers,
    )
    assert after.status_code == 200
    body = after.json()
    assert body["cajas_incluidas"] == before_count + 1
    before_cents = int(before.json()["subtotal_general_ars"].replace(".", ""))
    after_cents = int(body["subtotal_general_ars"].replace(".", ""))
    assert after_cents == before_cents + 4000
    by_id = {item["caja"]["id"]: item for item in body["cajas"]}
    assert activa_id in by_id
    assert by_id[activa_id]["saldo_ars"] == "40.00"
    assert archivada_id not in by_id
    assert len(body["cajas"]) == body["cajas_incluidas"]


@pytest.mark.asyncio
async def test_get_saldo_general_escribano_returns_403(
    client: AsyncClient,
    escribano_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/api/v1/cajas/saldo-general",
        headers=escribano_headers,
    )
    assert response.status_code == 403
    assert response.json()["detail"]


@pytest.mark.asyncio
async def test_get_saldo_general_without_token_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/cajas/saldo-general")
    assert response.status_code == 401
    assert response.json()["detail"]
