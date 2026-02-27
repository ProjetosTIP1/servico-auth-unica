from datetime import datetime, timedelta, timezone

from core.ports.service import ITokenService
from core.ports.repository import ITokenRepository, IUserRepository

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
        self, token_repository: ITokenRepository, user_repository: IUserRepository
    ):
        self.token_repository: ITokenRepository = token_repository
        self.user_repository: IUserRepository = user_repository

    def _get_time_to_expire(self, type: TokenType) -> timedelta:
        """Return the TTL duration for the given token type."""
        if type == TokenType.ACCESS:
            return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        elif type == TokenType.REFRESH:
            return timedelta(days=settings.REFRESH_TOKEN_EXPIRES_DAYS)
        return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    async def _validate_refresh_token(self, refresh_token_str: str) -> bool:
        try:
            token_model = await self.token_repository.get_token_by_string(
                refresh_token_str
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
                    await self._handle_security_breach(token_model.user_id)
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
        # Implement logic to create an access token based on the provided token creation model
        try:
            # Create the access token using the helper function
            access_token: str = create_jwt_token(
                data={"sub": user.username},
                expires_delta=self._get_time_to_expire(TokenType.ACCESS),
                token_type="access",
            )

            # Save the token in the repository (e.g., database)
            await self.token_repository.create_access_token(
                TokenCreateModel(
                    user_id=user.id,
                    token=access_token,
                    parent_token=parent_token,
                    expires_at=datetime.now(timezone.utc)
                    + self._get_time_to_expire(TokenType.ACCESS),
                    type=TokenType.ACCESS,
                )
            )

            # Return the created token as a response model
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
                data={"sub": str(user.username)},
                expires_delta=self._get_time_to_expire(TokenType.REFRESH),
                token_type="refresh",
            )

            await self.token_repository.create_refresh_token(
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
            # Validate the token
            if not await self._validate_refresh_token(token.refresh_token):
                raise TokenRevokedException("Invalid or revoked refresh token")

            user = await self.user_repository.get_user_by_id(token.user_id)
            if not user:
                raise UserNotFoundException("User not found")

            # Create the token pair
            refresh_token: str = await self.create_refresh_token(
                user, token.refresh_token
            )
            access_token: str = await self.create_access_token(user, refresh_token)

            # Revoke the old refresh token
            await self.token_repository.revoke_token(token.access_token)
            await self.token_repository.revoke_token(token.refresh_token)

            # Return the token pair
            return TokenResponseModel(
                access_token=access_token,
                refresh_token=refresh_token,
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
            token_model = await self.token_repository.get_last_refresh_token(
                user_id=user_id
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
            # Note: repository update typically takes a TokenUpdateModel and updates by token string
            # This implementation assumes the repository knows how to handle it.
            token_model = await self.token_repository.update(token)
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
            # We look up the token model by its string first
            token_model = await self.token_repository.get_token_by_string(
                token_response
            )
            if not token_model:
                raise TokenRevokedException("Token not found")
            await self.token_repository.revoke_token(token_model.token)
        except Exception as e:
            logger.error(
                message=f"Error revoking token: {e}",
                error_path="TokenService.revoke_token",
            )
            raise e

    async def logout(self, auth_user_id: int, token: TokenRequestModel) -> None:
        try:
            # Validate the token
            if not token.access_token or not token.refresh_token:
                raise TokenRevokedException("Invalid token")

            # Validate the user
            user: UserType = await self.user_repository.get_user_by_id(auth_user_id)
            if not user:
                raise UserNotFoundException()

            # Validate the token
            if not await self._validate_refresh_token(token.refresh_token):
                raise TokenRevokedException("Invalid or revoked refresh token")

            # Revoke the token
            await self.token_repository.revoke_token(token.refresh_token)
            await self.token_repository.revoke_token(token.access_token)
        except Exception as e:
            logger.error(
                message=f"Error logging out: {e}",
                error_path="TokenService.logout",
            )
            raise e

    async def login(self, username: str, password: str) -> TokenResponseModel:
        try:
            # Validate the credentials
            if not username or not password:
                raise InvalidCredentialsException()

            # Validate the user and password
            user: UserType = await self.user_repository.get_user_by_username(username)
            if not user:
                raise InvalidCredentialsException()

            hashed_password = await self.user_repository.get_user_hashed_password(
                username
            )
            if not verify_password(password, hashed_password):
                raise InvalidCredentialsException()

            # Create the refresh token
            refresh_token: str = await self.create_refresh_token(user, "")

            # Create the access token
            access_token: str = await self.create_access_token(user, refresh_token)

            # Return the token response model
            return TokenResponseModel(
                access_token=access_token,
                refresh_token=refresh_token,
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
            token_model = await self.token_repository.get_token_by_string(token)
            if not token_model:
                raise TokenRevokedException("Token not found")
            if token_model.type != TokenType.ACCESS:
                raise TokenRevokedException("Token is not an access token")
            if token_model.revoked:
                raise TokenRevokedException("Token is revoked")
            if token_model.expires_at < datetime.now(timezone.utc):
                raise TokenRevokedException("Token is expired")
            if not validate_token(token_model.token):
                raise TokenRevokedException("Token is invalid")
            return True if validate_token(token_model.token) else False
        except Exception as e:
            logger.error(
                message=f"Error validating access token: {e}",
                error_path="TokenService.validate_access_token",
            )
            raise e

    async def _handle_security_breach(self, user_id: int) -> None:
        """
        Handle a security breach (token reuse detection).
        Revokes all tokens associated with the user.
        """
        try:
            logger.warning(
                message=f"SECURITY BREACH: Token reuse detected for user {user_id}. Revoking all tokens.",
                error_path="TokenService._handle_security_breach",
            )
            await self.token_repository.revoke_all_user_tokens(user_id)
        except Exception as e:
            logger.error(
                message=f"Error handling security breach: {e}",
                error_path="TokenService._handle_security_breach",
            )
