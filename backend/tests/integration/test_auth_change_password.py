"""Integration tests for POST /api/v1/auth/change-password (T010)."""

import pytest
from httpx import AsyncClient

from uuid import uuid4

from app.core.security import INVALID_CREDENTIALS_MESSAGE, hash_password
from app.db.session import SessionLocal
from app.models.usuario import Usuario

CHANGE_PATH = "/api/v1/auth/change-password"
LOGIN_PATH = "/api/v1/auth/login"


def _create_user(prefix: str, password: str) -> str:
    username = f"{prefix}_{uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        db.add(
            Usuario(
                username=username,
                password_hash=hash_password(password),
                rol="escribano",
            )
        )
        db.commit()
    finally:
        db.close()
    return username


@pytest.mark.asyncio
async def test_change_password_public_returns_204_and_old_login_fails(
    client: AsyncClient,
) -> None:
    username = _create_user("chg_public_ok", "OldPass12")

    response = await client.post(
        CHANGE_PATH,
        json={
            "username": username,
            "current_password": "OldPass12",
            "new_password": "NuevaClave1",
            "new_password_confirm": "NuevaClave1",
        },
    )
    assert response.status_code == 204
    assert response.content == b""

    old_login = await client.post(
        LOGIN_PATH,
        json={"username": username, "password": "OldPass12"},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        LOGIN_PATH,
        json={"username": username, "password": "NuevaClave1"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["access_token"]


@pytest.mark.asyncio
async def test_change_password_public_invalid_credentials_match_login_message(
    client: AsyncClient,
) -> None:
    failed_login = await client.post(
        LOGIN_PATH,
        json={"username": "no-existe", "password": "x"},
    )
    failed_change = await client.post(
        CHANGE_PATH,
        json={
            "username": "no-existe",
            "current_password": "x",
            "new_password": "NuevaClave1",
            "new_password_confirm": "NuevaClave1",
        },
    )
    assert failed_change.status_code == 401
    assert failed_change.json()["detail"] == failed_login.json()["detail"]
    assert failed_change.json()["detail"] == INVALID_CREDENTIALS_MESSAGE


@pytest.mark.asyncio
async def test_change_password_public_rejects_confirm_mismatch(
    client: AsyncClient,
) -> None:
    response = await client.post(
        CHANGE_PATH,
        json={
            "username": "admin",
            "current_password": "admin",
            "new_password": "NuevaClave1",
            "new_password_confirm": "OtraClave12",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password_public_rejects_short_password(
    client: AsyncClient,
) -> None:
    response = await client.post(
        CHANGE_PATH,
        json={
            "username": "admin",
            "current_password": "admin",
            "new_password": "short",
            "new_password_confirm": "short",
        },
    )
    assert response.status_code == 422


ME_PATH = "/api/v1/auth/me/password"


async def _login(client: AsyncClient, username: str, password: str) -> str:
    response = await client.post(
        LOGIN_PATH,
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_change_password_me_returns_204_and_revokes_old_token(
    client: AsyncClient,
) -> None:
    username = _create_user("chg_me_ok", "OldPass12")
    token = await _login(client, username, "OldPass12")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        ME_PATH,
        json={
            "current_password": "OldPass12",
            "new_password": "NuevaClave1",
            "new_password_confirm": "NuevaClave1",
        },
        headers=headers,
    )
    assert response.status_code == 204

    stale = await client.get("/api/v1/cajas", headers=headers)
    assert stale.status_code == 401

    new_token = await _login(client, username, "NuevaClave1")
    fresh = await client.get(
        "/api/v1/cajas",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert fresh.status_code == 200


@pytest.mark.asyncio
async def test_change_password_me_wrong_current_keeps_session(
    client: AsyncClient,
) -> None:
    username = _create_user("chg_me_wrong", "OldPass12")
    token = await _login(client, username, "OldPass12")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        ME_PATH,
        json={
            "current_password": "bad-password",
            "new_password": "NuevaClave1",
            "new_password_confirm": "NuevaClave1",
        },
        headers=headers,
    )
    assert response.status_code == 401
    assert response.json()["detail"] == INVALID_CREDENTIALS_MESSAGE

    still_valid = await client.get("/api/v1/cajas", headers=headers)
    assert still_valid.status_code == 200


@pytest.mark.asyncio
async def test_change_password_me_unauthenticated_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.post(
        ME_PATH,
        json={
            "current_password": "OldPass12",
            "new_password": "NuevaClave1",
            "new_password_confirm": "NuevaClave1",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_me_escribano_ok(client: AsyncClient) -> None:
    username = _create_user("chg_me_esc", "OldPass12")
    token = await _login(client, username, "OldPass12")

    response = await client.post(
        ME_PATH,
        json={
            "current_password": "OldPass12",
            "new_password": "NuevaClave1",
            "new_password_confirm": "NuevaClave1",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_change_password_me_rejects_username_in_body(
    client: AsyncClient,
) -> None:
    username = _create_user("chg_me_idor", "OldPass12")
    token = await _login(client, username, "OldPass12")

    response = await client.post(
        ME_PATH,
        json={
            "username": "admin",
            "current_password": "OldPass12",
            "new_password": "NuevaClave1",
            "new_password_confirm": "NuevaClave1",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422

