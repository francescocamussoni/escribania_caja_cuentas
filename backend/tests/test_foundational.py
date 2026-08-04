import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from sqlalchemy import text


def test_database_connection(db_session: Session) -> None:
    assert db_session.execute(text("SELECT 1")).scalar_one() == 1


@pytest.mark.asyncio
async def test_async_client_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
