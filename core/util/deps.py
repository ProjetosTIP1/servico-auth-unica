"""
FastAPI dependency providers.

This module is the Composition Root for the Application layer — the single
place that wires abstract ports to concrete infrastructure adapters.
Everything above (route handlers, use-case services) stays decoupled from
implementation details because dependencies are injected here.
"""

from core.ports.service import ITokenService, IIntegrationService
from core.ports.repository import (
    IUserRepository,
    ITokenRepository,
    ISgaRepository,
    ISamIntegrationRepository,
    IApplicationRepository,
)
from core.helpers.authentication_helper import validate_token
from typing import Annotated
from functools import lru_cache

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config.settings import settings
from core.ports.infrastructure import IDatabase
from core.infrastructure.database_manager import DatabaseManager
from core.infrastructure.microsoft_auth_adapter import (
    MicrosoftAuthAdapter,
    MicrosoftAuthError,
)
from core.infrastructure.integration_adapters import (
    SgaPolarsAdapter,
    SamIntegrationAdapter,
)

from core.repositories.user_repository import UserRepository
from core.repositories.token_repository import TokenRepository
from core.repositories.application_repository import ApplicationRepository
from core.models.user_models import MicrosoftUserIdentity, UserType
from core.ports.service import IMicrosoftAuthService

from core.services.microsoft_login_service import MicrosoftLoginService
from core.services.token_service import TokenService as TokenServiceImpl
from core.services.user_service import UserService as UserServiceImpl
from core.services.application_service import (
    ApplicationService as ApplicationServiceImpl,
)
from core.services.image_usecase import ImageUsecase
from integration.integration_service import IntegrationService

# ── Bearer token extractor ─────────────────────────────────────────────────────
_bearer_scheme = HTTPBearer(auto_error=False)


# ── Infrastructure adapter factory ────────────────────────────────────────────
def get_token_from_request(request: Request) -> str | None:
    token = request.cookies.get(settings.COOKIE_ACCESS_TOKEN_NAME)
    if token:
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    return None


def get_refresh_token_from_request(request: Request) -> str | None:
    token = request.cookies.get(settings.COOKIE_REFRESH_TOKEN_NAME)
    if token:
        return token

    return None


@lru_cache(maxsize=1)
def _get_ms_auth_adapter() -> IMicrosoftAuthService:
    return MicrosoftAuthAdapter()


# ── Use-case factory ──────────────────────────────────────────────────────────


def get_database_manager(request: Request) -> DatabaseManager:
    db_manager = request.app.state.db_manager
    if db_manager is None or not db_manager.is_initialized:
        raise HTTPException(status_code=500, detail="Database manager not initialized")
    return db_manager


def get_mariadb_database(
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> IDatabase:
    """Provide the MariaDB database instance."""
    if db_manager.mariadb is None:
        raise HTTPException(
            status_code=500, detail="MariaDB connection not initialized"
        )
    return db_manager.mariadb


def get_token_repository() -> ITokenRepository:
    """Provide a new instance of the TokenRepository."""
    return TokenRepository()


def get_user_repository() -> IUserRepository:
    """Provide a new instance of the UserRepository."""
    return UserRepository()


def get_token_service(
    token_repository: ITokenRepository = Depends(get_token_repository),
    user_repository: IUserRepository = Depends(get_user_repository),
    mariadb: IDatabase = Depends(get_mariadb_database),
) -> TokenServiceImpl:
    """Provide a fully wired `TokenService` to the route handler."""
    return TokenServiceImpl(
        token_repository=token_repository, user_repository=user_repository, db=mariadb
    )


def get_user_service(
    user_repository: IUserRepository = Depends(get_user_repository),
    mariadb: IDatabase = Depends(get_mariadb_database),
) -> UserServiceImpl:
    """Provide a fully wired `UserService` to the route handler."""
    return UserServiceImpl(user_repository=user_repository, db=mariadb)


def get_application_repository() -> IApplicationRepository:
    """Provide a new instance of the ApplicationRepository."""
    return ApplicationRepository()


def get_application_service(
    application_repository: IApplicationRepository = Depends(
        get_application_repository
    ),
    mariadb: IDatabase = Depends(get_mariadb_database),
) -> ApplicationServiceImpl:
    """Provide a fully wired `ApplicationService` to the route handler."""
    return ApplicationServiceImpl(
        application_repository=application_repository, db=mariadb
    )


def get_image_usecase() -> ImageUsecase:
    """Provide a new instance of the ImageUsecase."""
    return ImageUsecase()


def get_microsoft_login_service(
    ms_auth: IMicrosoftAuthService = Depends(_get_ms_auth_adapter),
    user_repo: IUserRepository = Depends(get_user_repository),
    token_service: TokenServiceImpl = Depends(get_token_service),
    image_usecase: ImageUsecase = Depends(get_image_usecase),
    mariadb: IDatabase = Depends(get_mariadb_database),
) -> MicrosoftLoginService:
    """Provide a fully wired `MicrosoftLoginService` to the route handler."""
    return MicrosoftLoginService(
        ms_auth=ms_auth,
        user_repo=user_repo,
        token_service=token_service,
        image_usecase=image_usecase,
        db=mariadb,
    )


@lru_cache(maxsize=1)
def get_sga_repository() -> ISgaRepository:
    return SgaPolarsAdapter()


@lru_cache(maxsize=1)
def get_sam_integration_repository() -> ISamIntegrationRepository:
    return SamIntegrationAdapter()


def provide_integration_service() -> IIntegrationService:
    """Standalone provider for scripts and cronjobs."""
    return IntegrationService(
        sga_repo=get_sga_repository(),
        sam_repo=get_sam_integration_repository(),
    )


def get_integration_service(
    sga_repo: Annotated[ISgaRepository, Depends(get_sga_repository)],
    sam_repo: Annotated[
        ISamIntegrationRepository, Depends(get_sam_integration_repository)
    ],
) -> IIntegrationService:
    """FastAPI provider."""
    return IntegrationService(sga_repo=sga_repo, sam_repo=sam_repo)


async def get_current_user(
    token: Annotated[str, Depends(get_token_from_request)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)],
    token_repo: Annotated[ITokenRepository, Depends(get_token_repository)],
    mariadb: Annotated[IDatabase, Depends(get_mariadb_database)],
) -> UserType:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    payload = validate_token(token)
    if payload is None:
        raise credentials_exception

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail="Invalid token type. Access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    cpf_cnpj = payload.get("sub")
    if cpf_cnpj is None:
        raise credentials_exception

    try:
        async with mariadb.transaction() as txn:
            token_model = await token_repo.get_token_by_string(txn, token)
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

    try:
        async with mariadb.transaction() as txn:
            user: UserType | None = await user_repo.get_user_by_cpfcnpj(txn, cpf_cnpj)
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


async def get_current_user_optional(
    token: Annotated[str | None, Depends(get_token_from_request)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)],
    token_repo: Annotated[ITokenRepository, Depends(get_token_repository)],
    mariadb: Annotated[IDatabase, Depends(get_mariadb_database)],
) -> UserType | None:
    """Version of get_current_user that doesn't raise if token is missing/invalid."""
    if token is None:
        return None

    try:
        payload = validate_token(token)
        if payload is None or payload.get("type") != "access":
            return None

        cpf_cnpj = payload.get("sub")
        if cpf_cnpj is None:
            return None

        async with mariadb.transaction() as txn:
            token_model = await token_repo.get_token_by_string(txn, token)
            if token_model is None or token_model.revoked:
                return None

            user: UserType | None = await user_repo.get_user_by_cpfcnpj(txn, cpf_cnpj)
            if user is None or not user.is_active:
                return None

            return user
    except Exception:
        return None


def get_current_token(
    token: Annotated[str | None, Depends(get_token_from_request)],
) -> str | None:
    if token is None:
        raise HTTPException(status_code=401, detail="Missing authentication token.")
    return token


async def require_microsoft_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    service: MicrosoftLoginService = Depends(get_microsoft_login_service),
) -> MicrosoftUserIdentity:
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
ApplicationServiceDeps = Annotated[
    ApplicationServiceImpl, Depends(get_application_service)
]
ImageUsecaseDeps = Annotated[ImageUsecase, Depends(get_image_usecase)]
DatabaseDeps = Annotated[IDatabase, Depends(get_mariadb_database)]
DatabaseManagerDeps = Annotated[DatabaseManager, Depends(get_database_manager)]
TokenDeps = Annotated[str | None, Depends(get_current_token)]
