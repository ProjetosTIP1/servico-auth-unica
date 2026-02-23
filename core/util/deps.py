"""
FastAPI dependency providers.

This module is the Composition Root for the Application layer — the single
place that wires abstract ports to concrete infrastructure adapters.
Everything above (route handlers, use-case services) stays decoupled from
implementation details because dependencies are injected here.
"""

from core.ports.service import ITokenService
from core.ports.repository import IUserRepository
from core.helpers.authentication_helper import validate_token
from typing import Annotated
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.infrastructure.microsoft_auth_adapter import (
    MicrosoftAuthAdapter,
    MicrosoftAuthError,
)
from core.helpers.authentication_helper import oauth2_scheme
from core.repositories.token_repository import TokenRepository
from core.models.user_models import MicrosoftUserIdentity, UserType
from core.ports.service import IMicrosoftAuthService

from core.services.microsoft_login_service import MicrosoftLoginService
from core.services.token_service import TokenService

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


def get_token_repository() -> TokenRepository:
    """Provide a new instance of the TokenRepository."""
    return TokenRepository()


def get_user_repository() -> IUserRepository:
    """Provide a new instance of the UserRepository."""
    return IUserRepository()


def get_token_service(
    token_repository: TokenRepository = Depends(get_token_repository),
) -> TokenService:
    """Provide a fully wired `TokenService` to the route handler."""
    return TokenService(token_repository=token_repository)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)],
) -> UserType:
    """
    Extract and validate user from JWT token.
    Returns a User object if authentication is successful.
    Raises HTTPException if authentication fails.
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = validate_token(token)
    if payload is None:
        raise credentials_exception

    username = payload.get("sub")
    if username is None:
        raise credentials_exception

    # Fetch user from database using the username from the token
    try:
        user: UserType = await user_repo.get_user_by_username(username)
        if user is None:
            raise credentials_exception
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    return user


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


AuthenticatedUser = Annotated[UserType, Depends(get_current_user)]
TokenService = Annotated[ITokenService, Depends(get_token_service)]
