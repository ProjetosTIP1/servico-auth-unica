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
from typing import Tuple

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.config.settings import settings

from core.models.user_models import MicrosoftUserIdentity, UserType, UserCreateType, UserUpdateType
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
        identity: MicrosoftUserIdentity | None = None
        user: UserType | None = None
        is_new_user = False
        
        # Step 1 — Validate the Microsoft token and extract the user identity
        try:
            identity = await self._ms_auth.validate_token(token)
        except Exception as e:
            logger.error(f"Microsoft token validation failed: {e}")
            raise

        if identity is None:
            raise RuntimeError("Microsoft token validation did not return an identity.")
        
        logger.info(
            message=f"Microsoft token validated for user oid={identity.oid} email={identity.email}"
        )

        
        # Step 2 — Check if the user exists in our system, or create/link as needed
        try:
            user, is_new_user = await self._check_user_sync(identity)
        except Exception as e:
            logger.error(f"User synchronization failed: {e}")
            raise RuntimeError("User synchronization failed after Microsoft token validation.")

        # Step 3 — Issue our own tokens
        # We need a refresh token and an access token
        refresh_token = await self._token_service.create_refresh_token(user, "")
        access_token = await self._token_service.create_access_token(
            user, refresh_token
        )

        tokens = TokenResponseModel(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=datetime.now(timezone.utc)
            + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        return MicrosoftLoginResult(
            tokens=tokens, user=user, identity=identity, is_new_user=is_new_user
        )
        
    async def _check_user_sync(self, identity: MicrosoftUserIdentity) -> Tuple[UserType, bool]:
        """
        Check if a user with the given Microsoft OID exists. If not, check by email or name.
        If a user with the same email or name exists, link the MS OID. Otherwise, create a new user.
        """
        user: UserType | None = None
        is_new_user = False
        
        name: str = identity.name.split("|")[0] if identity.name else identity.preferred_username or identity.email.split("@")[0]
        try:
            user = await self._user_repo.get_user_by_ms_oid(identity.oid)
            if user:
                return user, is_new_user

            # No user with this MS OID, check by email
            user = await self._user_repo.get_user_by_email(identity.email)
            if user:
                # Link MS OID to existing user
                await self._user_repo.update_user(
                    user.id, UserUpdateType(ms_oid=identity.oid)
                )
                return await self._user_repo.get_user_by_id(user.id), is_new_user
            
            # No user with this email, check by name
            users = await self._user_repo.search_users_by_name(name)
            if users:
                # Link MS OID to the first matching user
                await self._user_repo.update_user(
                    users[0].id, UserUpdateType(ms_oid=identity.oid)
                )
                return await self._user_repo.get_user_by_id(users[0].id), is_new_user

            # No user with this email or name, create new user
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
            return await self._user_repo.create_user(new_user_data, hashed_password), True
        except Exception as e:
            logger.error(f"Database error during user sync: {e}")
            raise RuntimeError("Internal error during user synchronization.")