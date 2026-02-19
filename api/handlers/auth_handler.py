"""
Auth route handlers — API layer.

These handlers are thin by design. Their only jobs are:
  1. Extract HTTP inputs (headers, body).
  2. Call the appropriate use-case service.
  3. Return an HTTP response.

No business logic lives here. Following the Single Responsibility Principle
(SRP), business decisions stay in the Application layer (services).
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from core.models.user_models import MicrosoftUserIdentity
from core.services.microsoft_login_service import MicrosoftLoginResult, MicrosoftLoginService
from core.util.deps import get_microsoft_login_service, require_microsoft_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request / Response schemas ─────────────────────────────────────────────────


class MicrosoftTokenRequest(BaseModel):
    """Body for the token-validation endpoint."""
    token: str


class MicrosoftLoginResponse(BaseModel):
    """Slim public-facing representation of a successful login result."""
    oid: str
    email: str
    name: str | None
    roles: list[str]
    is_new_user: bool


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post(
    "/microsoft/validate",
    response_model=MicrosoftLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a Microsoft-issued token",
    description=(
        "Accepts a raw Microsoft JWT (id_token or access_token obtained by the "
        "frontend via MSAL.js / MSAL Python) and validates it against Azure AD's "
        "public keys.  Returns the verified user identity on success."
    ),
)
async def validate_microsoft_token(
    body: MicrosoftTokenRequest,
    service: MicrosoftLoginService = Depends(get_microsoft_login_service),
) -> MicrosoftLoginResponse:
    """
    POST /auth/microsoft/validate

    Frontend flow reminder:
      1. User clicks "Sign in with Microsoft" on the frontend.
      2. Frontend (using MSAL.js) redirects to Microsoft login.
      3. Microsoft returns an `id_token` / `access_token` to the frontend.
      4. Frontend sends that token to this endpoint.
      5. This endpoint validates and returns the user's identity.
    """
    result: MicrosoftLoginResult = await service.execute(token=body.token)

    return MicrosoftLoginResponse(
        oid=result.identity.oid,
        email=result.identity.email,
        name=result.identity.name,
        roles=result.identity.roles,
        is_new_user=result.is_new_user,
    )


@router.get(
    "/me",
    response_model=MicrosoftUserIdentity,
    status_code=status.HTTP_200_OK,
    summary="Get the current authenticated user",
    description=(
        "Protected endpoint. Pass a valid Microsoft JWT in the "
        "Authorization: Bearer <token> header."
    ),
)
async def get_current_user(
    user: MicrosoftUserIdentity = Depends(require_microsoft_user),
) -> MicrosoftUserIdentity:
    """
    GET /auth/me

    Example of a route protected by `require_microsoft_user`.
    Any other endpoint in the app can use the same dependency:

        @router.get("/orders")
        async def list_orders(
            user: MicrosoftUserIdentity = Depends(require_microsoft_user)
        ):
            # `user.oid` is the verified Azure AD user — safe to use.
            ...
    """
    return user
