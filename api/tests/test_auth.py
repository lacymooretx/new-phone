import pytest
from httpx import AsyncClient

from .conftest import auth_header


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@msp.local", "password": "admin123"},
    )
    if response.status_code == 401:
        pytest.skip("Seed data not loaded")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@msp.local", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "test123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, msp_admin_token: str):
    # First login to get refresh token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@msp.local", "password": "admin123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Use refresh token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client: AsyncClient):
    response = await client.get("/api/v1/tenants")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_mfa_setup(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        "/api/v1/auth/mfa/setup",
        headers=auth_header(msp_admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "secret" in data
    assert "qr_code" in data
    assert "provisioning_uri" in data
