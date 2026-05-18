"""
Shared pytest fixtures.

Uses an in-memory SQLite database so no real Postgres is needed for tests.
Redis calls are patched in individual test files.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session, monkeypatch):
    """FastAPI TestClient with DB overridden to SQLite."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Patch Redis rate-limit check so it never raises
    monkeypatch.setattr(
        "app.api.v1.portfolio._check_rate_limit_redis",
        lambda user_id: None,
    )

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    """Register + login a test user and return auth headers."""
    client.post("/api/v1/auth/register", json={
        "email": "test@portai.com",
        "name": "Test User",
        "password": "securepass123",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "test@portai.com",
        "password": "securepass123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
