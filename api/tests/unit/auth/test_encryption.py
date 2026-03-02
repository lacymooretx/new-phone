"""Tests for new_phone.auth.encryption — Fernet encrypt/decrypt."""

import pytest

import new_phone.auth.encryption as enc_module
from new_phone.auth.encryption import decrypt_value, encrypt_value


@pytest.fixture(autouse=True)
def _reset_fernet():
    """Reset the module-level Fernet singleton between tests."""
    enc_module._fernet = None
    yield
    enc_module._fernet = None


class TestEncryptDecrypt:
    def test_roundtrip(self):
        plaintext = "my-sip-password-123"
        ciphertext = encrypt_value(plaintext)
        assert decrypt_value(ciphertext) == plaintext

    def test_ciphertext_differs_from_plaintext(self):
        plaintext = "secret-value"
        ciphertext = encrypt_value(plaintext)
        assert ciphertext != plaintext

    def test_different_ciphertexts_for_same_input(self):
        """Fernet uses a random IV so encrypting the same value twice gives different results."""
        c1 = encrypt_value("same-value")
        c2 = encrypt_value("same-value")
        assert c1 != c2

    def test_decrypt_invalid_ciphertext_raises(self):
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_value("not-valid-fernet-ciphertext")

    def test_encrypt_returns_nonempty_string(self):
        result = encrypt_value("x")
        assert isinstance(result, str)
        assert len(result) > 0
