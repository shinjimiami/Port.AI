"""Integration tests for auth and portfolio API endpoints."""
import pytest


# ── Auth ───────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_register_success(self, client):
        r = client.post("/api/v1/auth/register", json={
            "email": "new@portai.com",
            "name": "New User",
            "password": "password123",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "new@portai.com"
        assert "password_hash" not in data

    def test_register_duplicate_email(self, client):
        payload = {"email": "dup@portai.com", "name": "User", "password": "password123"}
        client.post("/api/v1/auth/register", json=payload)
        r = client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 409

    def test_register_weak_password(self, client):
        r = client.post("/api/v1/auth/register", json={
            "email": "weak@portai.com",
            "name": "User",
            "password": "short",
        })
        assert r.status_code == 422

    def test_login_success(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "login@portai.com",
            "name": "Login User",
            "password": "password123",
        })
        r = client.post("/api/v1/auth/login", json={
            "email": "login@portai.com",
            "password": "password123",
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "wrongpw@portai.com",
            "name": "User",
            "password": "password123",
        })
        r = client.post("/api/v1/auth/login", json={
            "email": "wrongpw@portai.com",
            "password": "wrongpassword",
        })
        assert r.status_code == 401

    def test_me_requires_auth(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_me_returns_user(self, client, registered_user):
        r = client.get("/api/v1/auth/me", headers=registered_user)
        assert r.status_code == 200
        assert r.json()["email"] == "test@portai.com"


# ── Portfolio ──────────────────────────────────────────────────────────────────

class TestPortfolio:
    def test_generate_requires_auth(self, client):
        r = client.post("/api/v1/portfolio/generate", json={
            "budget": 5000,
            "horizon": "6 months",
            "asset_classes": ["US_STOCKS"],
        })
        assert r.status_code == 401

    def test_generate_returns_202(self, client, registered_user, monkeypatch):
        # Patch Celery so the task doesn't actually run
        monkeypatch.setattr(
            "app.tasks.portfolio.generate_portfolio_task.delay",
            lambda *args, **kwargs: None,
        )
        r = client.post(
            "/api/v1/portfolio/generate",
            json={"budget": 5000, "horizon": "6 months", "asset_classes": ["US_STOCKS"]},
            headers=registered_user,
        )
        assert r.status_code == 202
        data = r.json()
        assert data["status"] == "pending"
        assert data["budget"] == 5000.0

    def test_generate_invalid_asset_class(self, client, registered_user):
        r = client.post(
            "/api/v1/portfolio/generate",
            json={"budget": 5000, "horizon": "6 months", "asset_classes": ["INVALID"]},
            headers=registered_user,
        )
        assert r.status_code == 422

    def test_generate_zero_budget(self, client, registered_user):
        r = client.post(
            "/api/v1/portfolio/generate",
            json={"budget": 0, "horizon": "6 months", "asset_classes": ["US_STOCKS"]},
            headers=registered_user,
        )
        assert r.status_code == 422

    def test_history_empty(self, client, registered_user):
        r = client.get("/api/v1/portfolio/history", headers=registered_user)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_portfolio_not_found(self, client, registered_user):
        r = client.get("/api/v1/portfolio/99999", headers=registered_user)
        assert r.status_code == 404

    def test_history_pagination(self, client, registered_user, monkeypatch):
        monkeypatch.setattr(
            "app.tasks.portfolio.generate_portfolio_task.delay",
            lambda *args, **kwargs: None,
        )
        payload = {"budget": 1000, "horizon": "1 year", "asset_classes": ["US_STOCKS"]}
        for _ in range(3):
            client.post("/api/v1/portfolio/generate", json=payload, headers=registered_user)

        r = client.get("/api/v1/portfolio/history?limit=2", headers=registered_user)
        assert r.status_code == 200
        assert len(r.json()) <= 2


# ── Health ─────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_endpoint(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["app"] == "PortAI"
