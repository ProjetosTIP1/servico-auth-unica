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

from core.models.user_models import (
    MicrosoftUserIdentity,
    UserType,
    UserCreateType,
    UserUpdateType,
)
from core.models.oauth_models import TokenResponseModel

from core.ports.service import IMicrosoftAuthService, ITokenService
from core.ports.repository import IUserRepository
from core.ports.infrastructure import IDatabase, ITransaction

from core.helpers.logger_helper import logger
from core.helpers.authentication_helper import get_password_hash
from core.services.image_usecase import ImageUsecase


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
        image_usecase: ImageUsecase,
        db: IDatabase,
    ) -> None:
        self._ms_auth = ms_auth
        self._user_repo = user_repo
        self._token_service = token_service
        self._image_usecase = image_usecase
        self.db = db

    async def execute(
        self, token: str, access_token: str | None = None
    ) -> MicrosoftLoginResult:
        """
        Validate the bearer token, sync the user, and issue session tokens.
        If access_token is provided, also syncs the profile picture.
        """
        identity: MicrosoftUserIdentity | None = None
        user: UserType | None = None
        is_new_user = False

        # Step 1 — Validate the Microsoft token and extract the user identity
        try:
            identity: MicrosoftUserIdentity | None = await self._ms_auth.validate_token(
                token
            )
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
            # We wrap user sync in its own transaction
            async with self.db.transaction() as txn:
                user, is_new_user = await self._check_user_sync(txn, identity)

                # Step 2.1 — Sync profile picture from Microsoft Graph if access_token is provided
                if access_token:
                    try:
                        photo_bytes = await self._ms_auth.get_user_profile_picture(
                            access_token
                        )
                        if photo_bytes:
                            await self._image_usecase.upsert_from_bytes(
                                txn, photo_bytes, user.id
                            )
                            logger.info(
                                f"Profile picture synced from Microsoft for user {user.id}"
                            )
                    except Exception as e:
                        # We don't want to fail the whole login if just the photo sync fails
                        logger.warning(
                            f"Failed to sync profile picture for user {user.id}: {e}"
                        )

        except Exception as e:
            logger.error(f"User synchronization failed: {e}")
            raise RuntimeError(
                f"User synchronization failed after Microsoft token validation: {e}"
            )

        # Step 3 — Issue our own tokens
        # Note: token_service methods will start their own transactions
        try:
            refresh_token: str = await self._token_service.create_refresh_token(
                user, ""
            )
            access_token: str = await self._token_service.create_access_token(
                user, refresh_token
            )
        except Exception as e:
            logger.error(f"Token issuance failed: {e}")
            raise RuntimeError("Failed to issue session tokens after Microsoft login.")

        tokens = TokenResponseModel(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=datetime.now(timezone.utc)
            + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        return MicrosoftLoginResult(
            tokens=tokens, user=user, identity=identity, is_new_user=is_new_user
        )

    async def _check_user_sync(
        self, txn: ITransaction, identity: MicrosoftUserIdentity
    ) -> Tuple[UserType, bool]:
        """
        Check if a user with the given Microsoft OID exists. If not, check by email or name.
        If a user with the same email or name exists, link the MS OID. Otherwise, create a new user.
        """
        user: UserType | None = None
        is_new_user = False

        name: str = (
            identity.name.split("|")[0]
            if identity.name
            else identity.preferred_username or identity.email.split("@")[0]
        )
        try:
            user = await self._user_repo.get_user_by_ms_oid(txn, identity.oid)
            if user:
                return user, is_new_user

            # No user with this MS OID, check by email
            user = await self._user_repo.get_user_by_email(txn, identity.email)
            if user:
                # Link MS OID to existing user
                await self._user_repo.update_user(
                    txn, user.id, UserUpdateType(ms_oid=identity.oid)
                )
                linked_user = await self._user_repo.get_user_by_id(txn, user.id)
                if linked_user is None:
                    raise RuntimeError("User not found after linking OID")
                return linked_user, is_new_user

            # No user with this email, check by name
            users = await self._user_repo.search_users_by_name(txn, name)
            if users:
                # Link MS OID to the first matching user
                await self._user_repo.update_user(
                    txn, users[0].id, UserUpdateType(ms_oid=identity.oid)
                )
                linked_user = await self._user_repo.get_user_by_id(txn, users[0].id)
                if linked_user is None:
                    raise RuntimeError("User not found after linking OID (by name)")
                return linked_user, is_new_user

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
            return await self._user_repo.create_user(
                txn, new_user_data, hashed_password
            ), True
        except Exception as e:
            logger.error(f"Database error during user sync: {e}")
            raise
