"""Rate limiting middleware using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from new_phone.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
)

# Rate limit strings for use in route decorators
RATE_LIMIT_AUTH = settings.rate_limit_auth
RATE_LIMIT_UPLOAD = "20/minute"
RATE_LIMIT_WEBHOOK = "60/minute"
