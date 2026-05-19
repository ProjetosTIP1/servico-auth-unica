from fastapi import HTTPException
from typing import Optional
from fastapi import APIRouter, Depends, status, Response
from pydantic import BaseModel

from core.models.user_models import UserType
from core.services.microsoft_login_service import (
    MicrosoftLoginResult,
    MicrosoftLoginService,
)
from core.util.deps import get_microsoft_login_service
from core.config.settings import settings

ms_router = APIRouter(prefix="/o/microsoft", tags=["Authentication"])


# ── Request / Response schemas ─────────────────────────────────────────────────


class MicrosoftTokenRequest(BaseModel):
    """Body for the token-validation endpoint."""

    token: str  # id_token
    access_token: Optional[str] = None  # Optional access token for Graph API (photo)


class MicrosoftLoginResponse(BaseModel):
    """Slim public-facing representation of a successful login result."""

    oid: Optional[str] = None
    email: str
    name: Optional[str] = None
    roles: list[str] = []
    is_new_user: bool = False
    user: Optional[UserType] = None


# ── Endpoints ──────────────────────────────────────────────────────────────────


@ms_router.post(
    path="/validate",
    response_model=MicrosoftLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a Microsoft-issued token",
    description=(
        "Accepts a raw Microsoft JWT (id_token or access_token obtained by the "
        "frontend via MSAL.js / MSAL Python) and validates it against Azure AD's "
        "public keys. Returns the verified user identity and sets session cookies on success."
    ),
)
async def validate_microsoft_token(
    body: MicrosoftTokenRequest,
    response: Response,
    service: MicrosoftLoginService = Depends(dependency=get_microsoft_login_service),
) -> MicrosoftLoginResponse:
    """
    POST /o/microsoft/validate
    """

    try:
        result: MicrosoftLoginResult = await service.execute(
            token=body.token, access_token=body.access_token
        )
        # Set cookies
        response.set_cookie(
            key=settings.COOKIE_ACCESS_TOKEN_NAME,
            value=result.tokens.access_token,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,  # ty:ignore[invalid-argument-type]
        )
        response.set_cookie(
            key=settings.COOKIE_REFRESH_TOKEN_NAME,
            value=result.tokens.refresh_token,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,  # ty:ignore[invalid-argument-type]
        )

        return MicrosoftLoginResponse(
            oid=result.identity.oid,
            email=result.identity.email,
            name=result.identity.name,
            roles=result.identity.roles,
            is_new_user=result.is_new_user,
            user=result.user,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {e}")
