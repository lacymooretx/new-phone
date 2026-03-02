import hashlib
import hmac

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def hash_token(token: str) -> str:
    """SHA-256 hash for tokens (refresh tokens, etc). Not for passwords."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(token: str, token_hash: str) -> bool:
    """Constant-time comparison of token against its SHA-256 hash."""
    return hmac.compare_digest(hash_token(token), token_hash)
