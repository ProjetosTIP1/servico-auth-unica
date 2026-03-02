"""
Microsoft Login Use Case — Application layer.

Responsibility: orchestrate the process of validating a Microsoft token
and resolving (or provisioning) the local user record.

Architecture notes:
- This service sits in the Application layer.
- It depends on `IMicrosoftAuthService` (abstraction), NOT on MSAL/httpx.
- It depends on `IUserRepository` (abstraction), NOT on MariaDB/SQLAlchemy.
- Both dependencies are injected — this makes the class trivially testable:
  pass mock implementations in tests, real adapters in production.
"""

import secrets
from dataclasses import dataclass

from core.models.user_models import MicrosoftUserIdentity, UserType, UserCreateType
from core.models.oauth_models import TokenResponseModel
from core.ports.service import IMicrosoftAuthService, ITokenService
from core.ports.repository import IUserRepository
from core.helpers.logger_helper import logger
from core.helpers.authentication_helper import get_password_hash


@dataclass
class MicrosoftLoginResult:
    """
    Output value object returned after a successful Microsoft login.

    Contains our system's tokens, the user information, and a flag
    indicating whether the user was just created.
    """

    tokens: TokenResponseModel
    user: UserType
    identity: MicrosoftUserIdentity
    is_new_user: bool = False


class MicrosoftLoginService:
    """
    Use case: validate a Microsoft-issued token, resolve (or provision)
    the local user record, and issue our own session tokens.
    """

    def __init__(
        self,
        ms_auth: IMicrosoftAuthService,
        user_repo: IUserRepository,
        token_service: ITokenService,
    ) -> None:
        self._ms_auth = ms_auth
        self._user_repo = user_repo
        self._token_service = token_service

    async def execute(self, token: str) -> MicrosoftLoginResult:
        """
        Validate the bearer token, sync the user, and issue session tokens.
        """
        # Step 1 — validate Microsoft token
        identity = await self._ms_auth.validate_token(token)

        logger.info(
            message=f"Microsoft token validated for user oid={identity.oid} email={identity.email}"
        )

        # Step 2 — Sync user with local database
        user = await self._user_repo.get_user_by_ms_oid(identity.oid)
        is_new_user = False

        if user is None:
            # Check if user exists by email (link MS account to existing email)
            user = await self._user_repo.get_user_by_email(identity.email)

            if user:
                # Update existing user with MS OID
                from core.models.user_models import UserUpdateType

                await self._user_repo.update_user(
                    user.id, UserUpdateType(ms_oid=identity.oid)
                )
                user = await self._user_repo.get_user_by_id(user.id)
            else:
                # Create new user
                new_user_data = UserCreateType(
                    username=identity.preferred_username or identity.email,
                    email=identity.email,
                    ms_oid=identity.oid,
                    full_name=identity.name,
                    first_name=identity.given_name,
                    last_name=identity.family_name,
                )
                # Random password since they login via MS
                random_password = secrets.token_urlsafe(32)
                hashed_password = get_password_hash(random_password)
                user = await self._user_repo.create_user(new_user_data, hashed_password)
                is_new_user = True

        # Step 3 — Issue our own tokens
        # We need a refresh token and an access token
        refresh_token = await self._token_service.create_refresh_token(user, "")
        access_token = await self._token_service.create_access_token(
            user, refresh_token
        )

        from datetime import datetime, timedelta, timezone
        from core.config.settings import settings

        tokens = TokenResponseModel(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=datetime.now(timezone.utc)
            + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        return MicrosoftLoginResult(
            tokens=tokens, user=user, identity=identity, is_new_user=is_new_user
        )

    async def get_auth_url(self, redirect_uri: str, scopes: list[str]) -> str:
        """
        (Optional) Generate the Microsoft login URL for frontend redirection.

        This is only needed if your frontend doesn't use MSAL.js and you want
        to handle the OAuth flow manually. If your frontend uses MSAL.js, it
        can construct the URL itself and you don't need this method.

        Args:
            redirect_uri: The URI that Microsoft should redirect back to after login.
            scopes: The list of permission scopes to request (e.g. ["User.Read"]).

        Returns:
            A URL string that the frontend can redirect the user to for Microsoft login.
        """
        return await self._ms_auth.get_auth_url(
            redirect_uri=redirect_uri, scopes=scopes
        )
