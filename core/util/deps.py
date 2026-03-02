"""
FastAPI dependency providers.

This module is the Composition Root for the Application layer — the single
place that wires abstract ports to concrete infrastructure adapters.
Everything above (route handlers, use-case services) stays decoupled from
implementation details because dependencies are injected here.
"""

from core.ports.service import ITokenService
from core.ports.repository import IUserRepository, ITokenRepository
from core.helpers.authentication_helper import validate_token
from typing import Annotated
from functools import lru_cache

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config.settings import settings
from core.infrastructure.database_manager import DatabaseManager
from core.infrastructure.microsoft_auth_adapter import (
    MicrosoftAuthAdapter,
    MicrosoftAuthError,
)

from core.repositories.user_repository import UserRepository
from core.repositories.token_repository import TokenRepository
from core.models.user_models import MicrosoftUserIdentity, UserType
from core.ports.service import IMicrosoftAuthService

from core.services.microsoft_login_service import MicrosoftLoginService
from core.services.token_service import TokenService as TokenServiceImpl
from core.services.user_service import UserService as UserServiceImpl

# ── Bearer token extractor ─────────────────────────────────────────────────────
# auto_error=False lets us return a custom 401 instead of FastAPI's default.
_bearer_scheme = HTTPBearer(auto_error=False)


# ── Infrastructure adapter factory ────────────────────────────────────────────
def get_token_from_request(request: Request) -> str | None:
    """
    Extract the access token from either the Authorization header or a cookie.
    Priority:
      1. Cookie (more secure for web apps)
      2. Authorization header (standard for APIs)
    """
    # 1. Check cookie
    token = request.cookies.get(settings.COOKIE_ACCESS_TOKEN_NAME)
    if token:
        return token

    # 2. Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    return None


def get_refresh_token_from_request(request: Request) -> str | None:
    """Extract the refresh token from either a cookie or the request body."""
    # 1. Check cookie
    token = request.cookies.get(settings.COOKIE_REFRESH_TOKEN_NAME)
    if token:
        return token

    return None


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


def get_database_manager(request: Request) -> DatabaseManager:
    """
    Dependency to get the database manager from the request state.
    This allows us to access the database connections initialized at startup.
    """
    db_manager = request.app.state.db_manager
    if db_manager is None or not db_manager.is_initialized:
        raise HTTPException(status_code=500, detail="Database manager not initialized")
    return db_manager


def get_token_repository(
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> TokenRepository:
    """Provide a new instance of the TokenRepository."""
    if db_manager.mariadb is None:
        raise HTTPException(
            status_code=500, detail="MariaDB connection not initialized"
        )
    return TokenRepository(db=db_manager.mariadb)


def get_user_repository(
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> IUserRepository:
    """Provide a new instance of the UserRepository."""
    if db_manager.mariadb is None:
        raise HTTPException(
            status_code=500, detail="MariaDB connection not initialized"
        )
    return UserRepository(db=db_manager.mariadb)


def get_token_service(
    token_repository: TokenRepository = Depends(get_token_repository),
    user_repository: IUserRepository = Depends(get_user_repository),
) -> TokenServiceImpl:
    """Provide a fully wired `TokenService` to the route handler."""
    return TokenServiceImpl(
        token_repository=token_repository, user_repository=user_repository
    )


def get_user_service(
    user_repository: IUserRepository = Depends(get_user_repository),
) -> UserServiceImpl:
    """Provide a fully wired `UserService` to the route handler."""
    return UserServiceImpl(user_repository=user_repository)


def get_microsoft_login_service(
    ms_auth: IMicrosoftAuthService = Depends(_get_ms_auth_adapter),
    user_repo: IUserRepository = Depends(get_user_repository),
    token_service: TokenServiceImpl = Depends(get_token_service),
) -> MicrosoftLoginService:
    """Provide a fully wired `MicrosoftLoginService` to the route handler."""
    return MicrosoftLoginService(
        ms_auth=ms_auth, user_repo=user_repo, token_service=token_service
    )


async def get_current_user(
    token: Annotated[str, Depends(get_token_from_request)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)],
    token_repo: Annotated[ITokenRepository, Depends(get_token_repository)],
) -> UserType:
    """
    Extract and validate the current user from the access token (cookie or header).

    Validation is performed in three layers:
      1. Cryptographic — signature + expiry (fast, no DB hit).
      2. Revocation    — checks the token has not been revoked/consumed in the
                         DB (covers logout, token rotation and security breaches).
      3. Identity      — confirms the user still exists and is active.

    Raises HTTPException (401/403) on any failure.
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    # ── 1. Cryptographic validation ───────────────────────────────────────────
    payload = validate_token(token)
    if payload is None:
        raise credentials_exception

    # Prevent refresh tokens from being used on protected resource endpoints.
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail="Invalid token type. Access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if username is None:
        raise credentials_exception

    # ── 2. DB-level revocation check ──────────────────────────────────────────
    # A token can be cryptographically valid but already revoked (e.g. after
    # logout, token rotation, or a security breach). We must reject it.
    try:
        token_model = await token_repo.get_token_by_string(token)
        if token_model is None or token_model.revoked:
            raise HTTPException(
                status_code=401,
                detail="Token has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token lookup error: {e}")

    # ── 3. Identity & active-status check ────────────────────────────────────
    try:
        user: UserType = await user_repo.get_user_by_username(username)
        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="User is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    return user


def get_current_token(
    token: Annotated[str | None, Depends(get_token_from_request)],
) -> str | None:
    """
    Extract and validate user from JWT token (cookie or header).
    Returns a User object if authentication is successful.
    Raises HTTPException if authentication fails.
    """
    if token is None:
        raise HTTPException(status_code=401, detail="Missing authentication token.")
    return token


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
TokenServiceDeps = Annotated[ITokenService, Depends(get_token_service)]
UserServiceDeps = Annotated[UserServiceImpl, Depends(get_user_service)]
TokenDeps = Annotated[str | None, Depends(get_current_token)]
