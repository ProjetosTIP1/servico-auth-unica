"""
FastAPI dependency providers.

This module is the Composition Root for the Application layer — the single
place that wires abstract ports to concrete infrastructure adapters.
Everything above (route handlers, use-case services) stays decoupled from
implementation details because dependencies are injected here.
"""

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.infrastructure.microsoft_auth_adapter import (
    MicrosoftAuthAdapter,
    MicrosoftAuthError,
)
from core.models.user_models import MicrosoftUserIdentity
from core.ports.service import IMicrosoftAuthService
from core.services.microsoft_login_service import MicrosoftLoginService

# ── Bearer token extractor ─────────────────────────────────────────────────────
# auto_error=False lets us return a custom 401 instead of FastAPI's default.
_bearer_scheme = HTTPBearer(auto_error=False)


# ── Infrastructure adapter factory ────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_ms_auth_adapter() -> IMicrosoftAuthService:
    """
    Single shared instance of the Microsoft auth adapter.

    `lru_cache(maxsize=1)` ensures we create the adapter (and its JWKS
    cache) only once per process — just like a singleton, but without the
    global-state anti-pattern.
    """
    return MicrosoftAuthAdapter()


# ── Use-case factory ──────────────────────────────────────────────────────────

def get_microsoft_login_service(
    ms_auth: IMicrosoftAuthService = Depends(_get_ms_auth_adapter),
) -> MicrosoftLoginService:
    """Provide a fully wired `MicrosoftLoginService` to the route handler."""
    return MicrosoftLoginService(ms_auth=ms_auth)


# ── Reusable "protected route" dependency ─────────────────────────────────────

async def require_microsoft_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    service: MicrosoftLoginService = Depends(get_microsoft_login_service),
) -> MicrosoftUserIdentity:
    """
    FastAPI dependency for routes that require a valid Microsoft login.

    Usage:
        @router.get("/me")
        async def me(user: MicrosoftUserIdentity = Depends(require_microsoft_user)):
            return user

    Returns:
        `MicrosoftUserIdentity` with the caller's verified claims.

    Raises:
        HTTP 401 if no token is provided or if the token is invalid/expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        result = await service.execute(token=credentials.credentials)
        return result.identity
    except MicrosoftAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
