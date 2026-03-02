import base64
import io

import pyotp
import qrcode

from new_phone.config import settings


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.mfa_issuer)


def generate_qr_code(provisioning_uri: str) -> str:
    """Generate a base64-encoded PNG QR code."""
    img = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
