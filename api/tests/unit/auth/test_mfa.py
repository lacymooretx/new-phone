"""Tests for new_phone.auth.mfa — TOTP secret, QR code, verification."""

import base64

import pyotp

from new_phone.auth.mfa import (
    generate_qr_code,
    generate_totp_secret,
    get_provisioning_uri,
    verify_totp,
)


class TestGenerateTotpSecret:
    def test_returns_base32_string(self):
        secret = generate_totp_secret()
        assert isinstance(secret, str)
        # base32 decode should not raise
        base64.b32decode(secret)

    def test_different_each_call(self):
        s1 = generate_totp_secret()
        s2 = generate_totp_secret()
        assert s1 != s2


class TestGetProvisioningUri:
    def test_contains_email_and_issuer(self):
        secret = generate_totp_secret()
        uri = get_provisioning_uri(secret, "user@example.com")
        assert "user@example.com" in uri or "user%40example.com" in uri
        assert "NewPhone" in uri
        assert uri.startswith("otpauth://totp/")


class TestGenerateQrCode:
    def test_returns_base64_png(self):
        secret = generate_totp_secret()
        uri = get_provisioning_uri(secret, "test@example.com")
        qr = generate_qr_code(uri)
        assert isinstance(qr, str)
        # Should be valid base64
        raw = base64.b64decode(qr)
        # PNG magic bytes
        assert raw[:4] == b"\x89PNG"


class TestVerifyTotp:
    def test_correct_code_returns_true(self):
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert verify_totp(secret, code) is True

    def test_wrong_code_returns_false(self):
        secret = generate_totp_secret()
        assert verify_totp(secret, "000000") is False
