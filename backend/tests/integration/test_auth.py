import pytest

ADMIN_CREDENTIALS = {"username": "admin", "password": "admin"}
INVALID_CREDENTIALS = {"username": "admin", "password": "wrong-password"}


@pytest.fixture
def admin_credentials() -> dict[str, str]:
    return dict(ADMIN_CREDENTIALS)


@pytest.mark.asyncio
async def test_login_success_returns_token_and_role(
    client, admin_credentials: dict[str, str]
) -> None:
    response = await client.post("/api/v1/auth/login", json=admin_credentials)

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 28800
    assert data["rol"] in {"secretaria", "escribano"}


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(client) -> None:
    response = await client.post("/api/v1/auth/login", json=INVALID_CREDENTIALS)

    assert response.status_code == 401
    body = response.json()
    assert "detail" in body
    assert isinstance(body["detail"], str)
    assert body["detail"]


@pytest.mark.asyncio
async def test_protected_route_without_token_returns_401(client) -> None:
    response = await client.get("/api/v1/cajas")

    assert response.status_code == 401
    body = response.json()
    assert body["detail"]


@pytest.mark.asyncio
async def test_expired_jwt_returns_401(client) -> None:
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    from app.core.config import get_settings

    settings = get_settings()
    expired_at = datetime.now(timezone.utc) - timedelta(hours=1)
    token = jwt.encode(
        {"sub": "admin", "rol": "secretaria", "exp": expired_at},
        settings.jwt_secret,
        algorithm="HS256",
    )

    response = await client.get(
        "/api/v1/cajas",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["detail"]

