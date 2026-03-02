from cryptography.fernet import Fernet, InvalidToken

from new_phone.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.trunk_encryption_key.encode())
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value using Fernet symmetric encryption."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string value."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt value — check NP_TRUNK_ENCRYPTION_KEY") from e
