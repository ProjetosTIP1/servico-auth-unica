from datetime import datetime, timedelta, timezone

from core.ports.service import ITokenService
from core.ports.repository import ITokenRepository, IUserRepository
from core.ports.infrastructure import IDatabase

from core.models.user_models import UserType
from core.models.oauth_models import (
    TokenResponseModel,
    TokenRequestModel,
    TokenCreateModel,
    TokenUpdateModel,
    TokenType,
)
from core.helpers.authentication_helper import (
    create_jwt_token,
    validate_token,
    verify_password,
)
from core.helpers.logger_helper import logger
from core.helpers.exceptions_helper import (
    SecurityBreachException,
    InvalidCredentialsException,
    TokenRevokedException,
    UserNotFoundException,
)
from core.config.settings import settings


class TokenService(ITokenService):
    def __init__(
        self, token_repository: ITokenRepository, user_repository: IUserRepository, db: IDatabase
    ):
        self.token_repository: ITokenRepository = token_repository
        self.user_repository: IUserRepository = user_repository
        self.db: IDatabase = db

    def _get_time_to_expire(self, type: TokenType) -> timedelta:
        """Return the TTL duration for the given token type."""
        if type == TokenType.ACCESS:
            return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        elif type == TokenType.REFRESH:
            return timedelta(days=settings.REFRESH_TOKEN_EXPIRES_DAYS)
        return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    async def _validate_refresh_token(self, refresh_token_str: str) -> bool:
        try:
            async with self.db.transaction() as txn:
                token_model = await self.token_repository.get_token_by_string(
                    txn, refresh_token_str
                )
                if not token_model:
                    return False

                # Allow validation to succeed if within grace period
                now = datetime.now(timezone.utc)
                if token_model.revoked:
                    consumed_at = token_model.consumed_at
                    if consumed_at and consumed_at.tzinfo is None:
                        consumed_at = consumed_at.replace(tzinfo=timezone.utc)
                    if not consumed_at or now > consumed_at:
                        await self._handle_security_breach(txn, token_model.user_id)
                        raise SecurityBreachException()

                payload = validate_token(refresh_token_str)
                if not payload:
                    return False
                return True
        except Exception as e:
            logger.error(
                message=f"Error validating refresh token: {e}",
                error_path="TokenService._validate_refresh_token",
            )
            raise e

    async def create_access_token(self, user: UserType, parent_token: str) -> str:
        try:
            # Create the access token using the helper function
            access_token: str = create_jwt_token(
                data={"sub": user.cpf_cnpj},
                expires_delta=self._get_time_to_expire(TokenType.ACCESS),
                token_type="access",
            )

            async with self.db.transaction() as txn:
                # Save the token in the repository
                await self.token_repository.create_access_token(
                    txn,
                    TokenCreateModel(
                        user_id=user.id,
                        token=access_token,
                        parent_token=parent_token,
                        expires_at=datetime.now(timezone.utc)
                        + self._get_time_to_expire(TokenType.ACCESS),
                        type=TokenType.ACCESS,
                    )
                )

            return access_token
        except Exception as e:
            logger.error(
                message=f"Error creating access token: {e}",
                error_path="TokenService.create_access_token",
            )
            raise e

    async def create_refresh_token(self, user: UserType, parent_token: str) -> str:
        try:
            refresh_token_str = create_jwt_token(
                data={"sub": str(user.cpf_cnpj)},
                expires_delta=self._get_time_to_expire(TokenType.REFRESH),
                token_type="refresh",
            )

            async with self.db.transaction() as txn:
                await self.token_repository.create_refresh_token(
                    txn,
                    TokenCreateModel(
                        user_id=user.id,
                        token=refresh_token_str,
                        parent_token=parent_token,
                        expires_at=datetime.now(timezone.utc)
                        + self._get_time_to_expire(TokenType.REFRESH),
                        type=TokenType.REFRESH,
                    )
                )

            return refresh_token_str
        except Exception as e:
            logger.error(
                message=f"Error creating refresh token: {e}",
                error_path="TokenService.create_refresh_token",
            )
            raise e

    async def create_token_pair(self, token: TokenRequestModel) -> TokenResponseModel:
        try:
            refresh_token: str | None = token.refresh_token
            access_token: str | None = token.access_token

            # Safe check for required tokens
            if not refresh_token or not access_token:
                raise InvalidCredentialsException(
                    "Refresh token and access token are required"
                )

            # Note: _validate_refresh_token handles its own transaction
            if not await self._validate_refresh_token(refresh_token):
                raise TokenRevokedException("Invalid or revoked refresh token")

            async with self.db.transaction() as txn:
                user = await self.user_repository.get_user_by_id(txn, token.user_id)
                if not user:
                    raise UserNotFoundException("User not found")

                # Create the token pair - these calls will each start their own transaction
                # but we could also refactor them to accept a txn.
                # However, for now let's keep it simple or wrap the whole thing.
                # Actually, better wrap the whole thing if we can.
            
            # Refactoring to use a single transaction for the whole operation
            async with self.db.transaction() as txn:
                 user = await self.user_repository.get_user_by_id(txn, token.user_id)
                 if not user:
                     raise UserNotFoundException("User not found")
                 
                 new_refresh_token_str = create_jwt_token(
                     data={"sub": str(user.cpf_cnpj)},
                     expires_delta=self._get_time_to_expire(TokenType.REFRESH),
                     token_type="refresh",
                 )

                 await self.token_repository.create_refresh_token(
                     txn,
                     TokenCreateModel(
                         user_id=user.id,
                         token=new_refresh_token_str,
                         parent_token=refresh_token,
                         expires_at=datetime.now(timezone.utc)
                         + self._get_time_to_expire(TokenType.REFRESH),
                         type=TokenType.REFRESH,
                     )
                 )

                 new_access_token_str = create_jwt_token(
                     data={"sub": user.cpf_cnpj},
                     expires_delta=self._get_time_to_expire(TokenType.ACCESS),
                     token_type="access",
                 )

                 await self.token_repository.create_access_token(
                     txn,
                     TokenCreateModel(
                         user_id=user.id,
                         token=new_access_token_str,
                         parent_token=new_refresh_token_str,
                         expires_at=datetime.now(timezone.utc)
                         + self._get_time_to_expire(TokenType.ACCESS),
                         type=TokenType.ACCESS,
                     )
                 )

                 # Revoke the old tokens
                 await self.token_repository.revoke_token(txn, access_token)
                 await self.token_repository.revoke_token(txn, refresh_token)

                 return TokenResponseModel(
                     access_token=new_access_token_str,
                     refresh_token=new_refresh_token_str,
                     expires_in=datetime.now(timezone.utc)
                     + self._get_time_to_expire(TokenType.ACCESS),
                 )
        except Exception as e:
            logger.error(
                message=f"Error creating token pair: {e}",
                error_path="TokenService.create_token_pair",
            )
            raise e

    async def get_last_refresh_token(self, user_id: str) -> TokenResponseModel:
        """Retrieve the last refresh token for the given user ID."""
        try:
            async with self.db.transaction() as txn:
                token_model = await self.token_repository.get_last_refresh_token(
                    txn, user_id=user_id
                )
                if not token_model:
                    raise TokenRevokedException("Refresh token not found")
                return TokenResponseModel(
                    access_token=token_model.token,
                    refresh_token=token_model.parent_token,
                    expires_in=token_model.expires_at,
                )
        except Exception as e:
            logger.error(
                message=f"Error getting last refresh token: {e}",
                error_path="TokenService.get_last_refresh_token",
            )
            raise e

    async def update(self, token: TokenUpdateModel) -> TokenResponseModel:
        """Update the given token and return the updated token."""
        try:
            async with self.db.transaction() as txn:
                token_model = await self.token_repository.update(txn, token)
                if not token_model:
                    raise TokenRevokedException("Token not found")
                return TokenResponseModel(
                    access_token=token_model.token,
                    refresh_token=token_model.parent_token,
                    expires_in=token_model.expires_at,
                )
        except Exception as e:
            logger.error(
                message=f"Error updating token: {e}",
                error_path="TokenService.update",
            )
            raise e

    async def revoke_token(self, token_response: str) -> None:
        """Revoke the given token."""
        try:
            async with self.db.transaction() as txn:
                token_model = await self.token_repository.get_token_by_string(
                    txn, token_response
                )
                if not token_model:
                    raise TokenRevokedException("Token not found")
                await self.token_repository.revoke_token(txn, token_model.token)
        except Exception as e:
            logger.error(
                message=f"Error revoking token: {e}",
                error_path="TokenService.revoke_token",
            )
            raise e

    async def logout(self, auth_user_id: int, token: TokenRequestModel) -> None:
        try:
            if not token.access_token or not token.refresh_token:
                raise TokenRevokedException("Invalid token")

            async with self.db.transaction() as txn:
                user: UserType | None = await self.user_repository.get_user_by_id(
                    txn, auth_user_id
                )
                if not user:
                    raise UserNotFoundException()

                # Inner validation check
                token_model = await self.token_repository.get_token_by_string(
                    txn, token.refresh_token
                )
                if not token_model or token_model.revoked:
                    raise TokenRevokedException("Invalid or revoked refresh token")

                await self.token_repository.revoke_token(txn, token.refresh_token)
                await self.token_repository.revoke_token(txn, token.access_token)
        except Exception as e:
            logger.error(
                message=f"Error logging out: {e}",
                error_path="TokenService.logout",
            )
            raise e

    async def login(self, cpfcnpj: str, password: str) -> TokenResponseModel:
        try:
            if not cpfcnpj or not password:
                raise InvalidCredentialsException()

            async with self.db.transaction() as txn:
                user: UserType | None = await self.user_repository.get_user_by_cpfcnpj(
                    txn, cpfcnpj
                )
                if not user:
                    raise InvalidCredentialsException()

                hashed_password: (
                    str | None
                ) = await self.user_repository.get_user_hashed_password(txn, user.email)
                if not hashed_password or not verify_password(password, hashed_password):
                    raise InvalidCredentialsException()

                refresh_token_str = create_jwt_token(
                    data={"sub": str(user.cpf_cnpj)},
                    expires_delta=self._get_time_to_expire(TokenType.REFRESH),
                    token_type="refresh",
                )

                await self.token_repository.create_refresh_token(
                    txn,
                    TokenCreateModel(
                        user_id=user.id,
                        token=refresh_token_str,
                        parent_token="",
                        expires_at=datetime.now(timezone.utc)
                        + self._get_time_to_expire(TokenType.REFRESH),
                        type=TokenType.REFRESH,
                    )
                )

                access_token_str = create_jwt_token(
                    data={"sub": user.cpf_cnpj},
                    expires_delta=self._get_time_to_expire(TokenType.ACCESS),
                    token_type="access",
                )

                await self.token_repository.create_access_token(
                    txn,
                    TokenCreateModel(
                        user_id=user.id,
                        token=access_token_str,
                        parent_token=refresh_token_str,
                        expires_at=datetime.now(timezone.utc)
                        + self._get_time_to_expire(TokenType.ACCESS),
                        type=TokenType.ACCESS,
                    )
                )

                return TokenResponseModel(
                    access_token=access_token_str,
                    refresh_token=refresh_token_str,
                    expires_in=datetime.now(timezone.utc)
                    + self._get_time_to_expire(TokenType.ACCESS),
                )
        except Exception as e:
            logger.error(
                message=f"Error creating token: {e}",
                error_path="TokenService.login",
            )
            raise e

    async def validate_access_token(self, token: str) -> bool:
        try:
            async with self.db.transaction() as txn:
                token_model = await self.token_repository.get_token_by_string(txn, token)
                if not token_model:
                    raise TokenRevokedException("Token not found")
                if token_model.type != TokenType.ACCESS:
                    raise TokenRevokedException("Token is not an access token")
                if token_model.revoked:
                    raise TokenRevokedException("Token is revoked")
                if token_model.expires_at < datetime.now(timezone.utc):
                    raise TokenRevokedException("Token is expired")
                if not validate_token(token_model.token):
                    return False
                return True
        except Exception as e:
            logger.error(
                message=f"Error validating access token: {e}",
                error_path="TokenService.validate_access_token",
            )
            raise e

    async def _handle_security_breach(self, txn: ITransaction, user_id: int) -> None:
        """
        Handle a security breach (token reuse detection).
        Revokes all tokens associated with the user.
        """
        try:
            logger.warning(
                message=f"SECURITY BREACH: Token reuse detected for user {user_id}. Revoking all tokens.",
                error_path="TokenService._handle_security_breach",
            )
            await self.token_repository.revoke_all_user_tokens(txn, user_id)
        except Exception as e:
            logger.error(
                message=f"Error handling security breach: {e}",
                error_path="TokenService._handle_security_breach",
            )
