from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.config import settings
from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.models.user import User
from new_phone.schemas.auth import (
    LoginRequest,
    MFAChallengeRequest,
    MFAChallengeResponse,
    MFASetupResponse,
    MFAVerifyRequest,
    PasswordChangeRequest,
    RefreshRequest,
    SSOCompleteRequest,
    SSOInitiateRequest,
    TokenResponse,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.auth_service import AuthService
from new_phone.services.sso_service import SSOService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Authenticate with email + password. Returns JWT or MFA challenge."""
    from new_phone.main import redis_client as _redis

    service = AuthService(db, redis=_redis)
    try:
        result = await service.authenticate(body.email, body.password)
    except ValueError as e:
        # Log failed login if user exists
        found = await db.execute(select(User).where(User.email == body.email))
        found_user = found.scalar_one_or_none()
        if found_user:
            await log_audit(db, found_user, request, "login_failed", "auth")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from None

    if result.get("mfa_required"):
        return MFAChallengeResponse(**result)

    # Log successful login — resolve user from the token
    user_result = await db.execute(select(User).where(User.email == body.email))
    logged_in_user = user_result.scalar_one_or_none()
    if logged_in_user:
        await log_audit(db, logged_in_user, request, "login", "auth")

    return TokenResponse(**result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Exchange a refresh token for a new token pair."""
    from new_phone.main import redis_client as _redis

    service = AuthService(db, redis=_redis)
    try:
        result = await service.refresh_tokens(body.refresh_token)
    except (ValueError, JWTError) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from None
    return TokenResponse(**result)


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Generate TOTP secret and QR code for MFA enrollment."""
    from new_phone.main import redis_client as _redis

    service = AuthService(db, redis=_redis)
    result = await service.setup_mfa(user)
    return MFASetupResponse(**result)


@router.post("/mfa/verify")
async def mfa_verify(
    body: MFAVerifyRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Confirm MFA setup by verifying a TOTP code."""
    from new_phone.main import redis_client as _redis

    service = AuthService(db, redis=_redis)
    try:
        await service.verify_mfa_setup(user, body.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/challenge")
async def mfa_challenge(
    body: MFAChallengeRequest,
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Submit TOTP code during login MFA challenge."""
    from new_phone.main import redis_client as _redis

    service = AuthService(db, redis=_redis)
    try:
        result = await service.complete_mfa_challenge(body.mfa_token, body.code)
    except (ValueError, JWTError) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from None
    return TokenResponse(**result)


@router.post("/change-password")
async def change_password(
    body: PasswordChangeRequest,
    user: Annotated[User, Depends(get_current_user)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Change the authenticated user's password."""
    from new_phone.main import redis_client as _redis

    service = AuthService(db, redis=_redis)
    try:
        await service.change_password(user.id, body.current_password, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None

    await log_audit(db, user, request, "password_changed", "auth")
    return {"message": "Password changed successfully"}


# -- SSO Endpoints -------------------------------------------------------------


@router.get("/sso/check-domain")
async def sso_check_domain(
    email: Annotated[str, Query(description="Email address to check for SSO")],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Check if an email domain has SSO configured (public endpoint)."""
    from new_phone.main import redis_client as _redis

    service = SSOService(db, _redis)
    return await service.check_domain(email)


@router.post("/sso/initiate")
async def sso_initiate(
    body: SSOInitiateRequest,
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Start SSO flow — returns authorization URL (public endpoint)."""
    from new_phone.main import redis_client as _redis

    service = SSOService(db, _redis)
    try:
        result = await service.initiate_sso(body.email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    return result


@router.get("/sso/callback")
async def sso_callback(
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    error: Annotated[str | None, Query()] = None,
    error_description: Annotated[str | None, Query()] = None,
):
    """Handle OIDC callback from IdP — exchanges code for tokens, redirects to frontend."""
    from urllib.parse import quote

    from new_phone.main import redis_client as _redis

    if error:
        # IdP returned an error — redirect to frontend with URL-encoded error
        safe_error = quote(error_description or error)
        return RedirectResponse(
            url=f"{settings.sso_frontend_url}/login?sso_error={safe_error}"
        )

    service = SSOService(db, _redis)
    try:
        result_state = await service.handle_callback(code, state)
    except ValueError as e:
        safe_error = quote(str(e))
        return RedirectResponse(
            url=f"{settings.sso_frontend_url}/login?sso_error={safe_error}"
        )

    # Redirect to frontend with state token for token retrieval
    return RedirectResponse(
        url=f"{settings.sso_frontend_url}/login?sso_complete={result_state}"
    )


@router.post("/sso/complete")
async def sso_complete(
    body: SSOCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Frontend calls this to exchange SSO state for JWT tokens."""
    from new_phone.main import redis_client as _redis

    service = SSOService(db, _redis)
    try:
        tokens = await service.complete_sso(body.state)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from None
    return TokenResponse(**tokens)
