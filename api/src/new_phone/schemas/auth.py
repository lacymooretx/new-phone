from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str  # base64-encoded PNG
    provisioning_uri: str


class MFAVerifyRequest(BaseModel):
    code: str


class MFAChallengeRequest(BaseModel):
    mfa_token: str  # temporary token from login
    code: str


class MFAChallengeResponse(BaseModel):
    mfa_required: bool = True
    mfa_token: str  # temporary token to use with /mfa/challenge
