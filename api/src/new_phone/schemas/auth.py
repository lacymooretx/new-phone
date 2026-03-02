from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_not_same_as_current(cls, v: str, info) -> str:
        if info.data.get("current_password") and v == info.data["current_password"]:
            msg = "New password must differ from current password"
            raise ValueError(msg)
        return v


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


class SSOInitiateRequest(BaseModel):
    email: EmailStr


class SSOCompleteRequest(BaseModel):
    state: str = Field(min_length=1, max_length=200)
