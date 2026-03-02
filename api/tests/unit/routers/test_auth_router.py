"""Tests for new_phone.routers.auth — login, refresh, MFA, SSO."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.routers import auth


@pytest.fixture
def app(mock_db, acme_admin_user):
    test_app = FastAPI()
    test_app.include_router(auth.router, prefix="/api/v1")

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_admin_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: acme_admin_user
    yield test_app
    test_app.dependency_overrides.clear()


class TestLoginEndpoint:
    async def test_success_returns_tokens(self, client):
        tokens = {
            "access_token": "access-jwt",
            "refresh_token": "refresh-jwt",
            "token_type": "bearer",
        }
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.authenticate = AsyncMock(return_value=tokens)

            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "admin@acme.com", "password": "correct"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["access_token"] == "access-jwt"
            assert data["token_type"] == "bearer"

    async def test_mfa_challenge_returned(self, client):
        mfa_result = {"mfa_required": True, "mfa_token": "mfa-jwt"}
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.authenticate = AsyncMock(return_value=mfa_result)

            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "admin@acme.com", "password": "correct"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["mfa_required"] is True

    async def test_wrong_credentials_401(self, client):
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.authenticate = AsyncMock(side_effect=ValueError("Invalid email or password"))

            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "admin@acme.com", "password": "wrong"},
            )
            assert resp.status_code == 401

    async def test_locked_account_401(self, client):
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.authenticate = AsyncMock(
                side_effect=ValueError("Account is temporarily locked")
            )

            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "admin@acme.com", "password": "any"},
            )
            assert resp.status_code == 401
            assert "locked" in resp.json()["detail"]


class TestRefreshEndpoint:
    async def test_success(self, client):
        tokens = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "token_type": "bearer",
        }
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.refresh_tokens = AsyncMock(return_value=tokens)

            resp = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "old-refresh"},
            )
            assert resp.status_code == 200
            assert resp.json()["access_token"] == "new-access"

    async def test_invalid_refresh_token_401(self, client):
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.refresh_tokens = AsyncMock(side_effect=ValueError("Invalid refresh token"))

            resp = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "bad-token"},
            )
            assert resp.status_code == 401


class TestMfaSetup:
    async def test_setup_returns_secret(self, client):
        setup_result = {
            "secret": "JBSWY3DPEHPK3PXP",
            "qr_code": "base64png...",
            "provisioning_uri": "otpauth://totp/...",
        }
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.setup_mfa = AsyncMock(return_value=setup_result)

            resp = await client.post("/api/v1/auth/mfa/setup")
            assert resp.status_code == 200
            data = resp.json()
            assert "secret" in data
            assert "qr_code" in data

    async def test_verify_success(self, client):
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.verify_mfa_setup = AsyncMock(return_value=True)

            resp = await client.post("/api/v1/auth/mfa/verify", json={"code": "123456"})
            assert resp.status_code == 200

    async def test_verify_wrong_code_400(self, client):
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.verify_mfa_setup = AsyncMock(side_effect=ValueError("Invalid code"))

            resp = await client.post("/api/v1/auth/mfa/verify", json={"code": "000000"})
            assert resp.status_code == 400


class TestMfaChallenge:
    async def test_success(self, client):
        tokens = {
            "access_token": "access-jwt",
            "refresh_token": "refresh-jwt",
            "token_type": "bearer",
        }
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.complete_mfa_challenge = AsyncMock(return_value=tokens)

            resp = await client.post(
                "/api/v1/auth/mfa/challenge",
                json={"mfa_token": "mfa-jwt", "code": "123456"},
            )
            assert resp.status_code == 200
            assert resp.json()["access_token"] == "access-jwt"

    async def test_wrong_code_401(self, client):
        with patch("new_phone.routers.auth.AuthService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.complete_mfa_challenge = AsyncMock(side_effect=ValueError("Invalid MFA code"))

            resp = await client.post(
                "/api/v1/auth/mfa/challenge",
                json={"mfa_token": "mfa-jwt", "code": "000000"},
            )
            assert resp.status_code == 401


class TestSsoCheckDomain:
    async def test_returns_sso_info(self, client):
        with patch("new_phone.routers.auth.SSOService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.check_domain = AsyncMock(
                return_value={"sso_available": True, "provider": "microsoft"}
            )

            resp = await client.get("/api/v1/auth/sso/check-domain?email=user@acme.com")
            assert resp.status_code == 200


class TestSsoInitiate:
    async def test_returns_auth_url(self, client):
        with patch("new_phone.routers.auth.SSOService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.initiate_sso = AsyncMock(
                return_value={"authorization_url": "https://login.microsoft.com/..."}
            )

            resp = await client.post(
                "/api/v1/auth/sso/initiate",
                json={"email": "user@acme.com"},
            )
            assert resp.status_code == 200

    async def test_missing_email_400(self, client):
        resp = await client.post("/api/v1/auth/sso/initiate", json={"email": ""})
        assert resp.status_code == 400


class TestSsoComplete:
    async def test_success(self, client):
        tokens = {
            "access_token": "sso-access",
            "refresh_token": "sso-refresh",
            "token_type": "bearer",
        }
        with patch("new_phone.routers.auth.SSOService") as MockService:
            mock_svc = MockService.return_value
            mock_svc.complete_sso = AsyncMock(return_value=tokens)

            resp = await client.post(
                "/api/v1/auth/sso/complete",
                json={"state": "valid-state-token"},
            )
            assert resp.status_code == 200
            assert resp.json()["access_token"] == "sso-access"
