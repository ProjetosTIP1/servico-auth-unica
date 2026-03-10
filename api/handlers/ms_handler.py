"""
Auth route handlers — API layer.

These handlers are thin by design. Their only jobs are:
  1. Extract HTTP inputs (headers, body).
  2. Call the appropriate use-case service.
  3. Return an HTTP response.

No business logic lives here. Following the Single Responsibility Principle
(SRP), business decisions stay in the Application layer (services).
"""

from typing import Optional
from fastapi import APIRouter, Depends, status, Response
from pydantic import BaseModel

from core.models.user_models import MicrosoftUserIdentity, UserType
from core.services.microsoft_login_service import (
    MicrosoftLoginResult,
    MicrosoftLoginService,
)
from core.util.deps import get_microsoft_login_service, require_microsoft_user
from core.config.settings import settings

ms_router = APIRouter(prefix="/o/microsoft", tags=["Authentication"])


# ── Request / Response schemas ─────────────────────────────────────────────────


class MicrosoftTokenRequest(BaseModel):
    """Body for the token-validation endpoint."""

    token: str


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
    result: MicrosoftLoginResult = await service.execute(token=body.token)

    # Set cookies
    response.set_cookie(
        key=settings.COOKIE_ACCESS_TOKEN_NAME,
        value=result.tokens.access_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    response.set_cookie(
        key=settings.COOKIE_REFRESH_TOKEN_NAME,
        value=result.tokens.refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )

    return MicrosoftLoginResponse(
        oid=result.identity.oid,
        email=result.identity.email,
        name=result.identity.name,
        roles=result.identity.roles,
        is_new_user=result.is_new_user,
        user=result.user,
    )


@ms_router.get(
    path="/login-url",
    response_model=str,
    status_code=status.HTTP_200_OK,
    summary="Get Microsoft login URL",
    description=(
        "Returns the URL that the frontend should redirect the user to for Microsoft login."
    ),
)
async def get_microsoft_login_url(
    service: MicrosoftLoginService = Depends(dependency=get_microsoft_login_service),
) -> str:
    """
    GET /o/microsoft/login-url

    Returns the URL that the frontend should redirect the user to for Microsoft login.
    """
    return await service.get_auth_url(
        redirect_uri="https://localhost:8000/o/microsoft/callback", scopes=["User.Read"]
    )


@ms_router.post(
    path="/callback",
    response_model=MicrosoftLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Handle Microsoft login callback",
    description=(
        "Handles the callback from Microsoft login. This endpoint is called by the frontend "
        "after the user has authenticated with Microsoft."
    ),
)
async def handle_microsoft_callback(
    code: str,
    redirect_uri: str,
    service: MicrosoftLoginService = Depends(dependency=get_microsoft_login_service),
) -> MicrosoftLoginResponse:
    """
    POST /o/microsoft/callback

    Handles the callback from Microsoft login. This endpoint is called by the frontend
    after the user has authenticated with Microsoft.

    The frontend should send the `code` and `redirect_uri` it received from Microsoft
    to this endpoint, which will exchange the code for a token and validate it.
    """
    raise NotImplementedError(
        "This endpoint is a placeholder for the full OAuth flow. Implement if needed."
    )


@ms_router.get(
    path="/me",
    response_model=MicrosoftUserIdentity,
    status_code=status.HTTP_200_OK,
    summary="Get the current authenticated user",
    description=(
        "Protected endpoint. Pass a valid Microsoft JWT in the "
        "Authorization: Bearer <token> header."
    ),
)
async def get_current_user(
    user: MicrosoftUserIdentity = Depends(dependency=require_microsoft_user),
) -> MicrosoftUserIdentity:
    """
    GET /o/microsoft/me

    Example of a route protected by `require_microsoft_user`.
    Any other endpoint in the app can use the same dependency:

        @router.get("/orders")
        async def list_orders(
            user: MicrosoftUserIdentity = Depends(dependency=require_microsoft_user)
        ):
            # `user.oid` is the verified Azure AD user — safe to use.
            ...
    """
    return user
