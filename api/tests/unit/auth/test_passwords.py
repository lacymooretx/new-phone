"""Tests for new_phone.auth.passwords — hashing and verification."""

from new_phone.auth.passwords import hash_password, hash_token, verify_password, verify_token


class TestHashPassword:
    def test_returns_nonempty_string(self):
        h = hash_password("secret123")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_different_salt_each_time(self):
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2

    def test_verify_correct_password(self):
        h = hash_password("correct-horse")
        assert verify_password("correct-horse", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct-horse")
        assert verify_password("wrong-horse", h) is False


class TestHashToken:
    def test_returns_hex_string(self):
        h = hash_token("my-refresh-token")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest

    def test_verify_correct_token(self):
        token = "my-refresh-token-abc123"
        h = hash_token(token)
        assert verify_token(token, h) is True

    def test_verify_wrong_token(self):
        h = hash_token("original-token")
        assert verify_token("different-token", h) is False
