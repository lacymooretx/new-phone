"""Tests for new_phone.auth.jwt — token creation and decoding."""

import uuid
from datetime import UTC, datetime

import pytest
from jose import JWTError

from new_phone.auth.jwt import (
    create_access_token,
    create_mfa_token,
    create_refresh_token,
    decode_token,
)

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000020")


class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token(USER_ID, TENANT_ID, "tenant_admin")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_contains_correct_claims(self):
        token = create_access_token(USER_ID, TENANT_ID, "tenant_admin", language="es")
        payload = decode_token(token)
        assert payload["sub"] == str(USER_ID)
        assert payload["tenant_id"] == str(TENANT_ID)
        assert payload["role"] == "tenant_admin"
        assert payload["language"] == "es"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_default_language_is_en(self):
        token = create_access_token(USER_ID, TENANT_ID, "tenant_user")
        payload = decode_token(token)
        assert payload["language"] == "en"

    def test_token_is_decodable(self):
        token = create_access_token(USER_ID, TENANT_ID, "msp_super_admin")
        payload = decode_token(token)
        assert payload["sub"] == str(USER_ID)


class TestCreateRefreshToken:
    def test_returns_token_and_expiry(self):
        token, expires_at = create_refresh_token(USER_ID)
        assert isinstance(token, str)
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(UTC)

    def test_contains_correct_claims(self):
        token, _ = create_refresh_token(USER_ID)
        payload = decode_token(token)
        assert payload["sub"] == str(USER_ID)
        assert payload["type"] == "refresh"
        assert "jti" in payload
        assert "exp" in payload


class TestCreateMfaToken:
    def test_returns_string(self):
        token = create_mfa_token(USER_ID)
        assert isinstance(token, str)

    def test_has_mfa_pending_type(self):
        token = create_mfa_token(USER_ID)
        payload = decode_token(token)
        assert payload["type"] == "mfa_pending"
        assert payload["sub"] == str(USER_ID)


class TestDecodeToken:
    def test_valid_token(self):
        token = create_access_token(USER_ID, TENANT_ID, "tenant_admin")
        payload = decode_token(token)
        assert payload["sub"] == str(USER_ID)

    def test_invalid_signature_raises(self):
        from jose import jwt

        token = jwt.encode(
            {"sub": "test", "type": "access"},
            "wrong-secret-key",
            algorithm="HS256",
        )
        with pytest.raises(JWTError):
            decode_token(token)

    def test_malformed_token_raises(self):
        with pytest.raises(JWTError):
            decode_token("not.a.valid.jwt.token")
