from datetime import datetime, timedelta, timezone
from core.ports.service import ITokenService
from core.ports.repository import ITokenRepository

from core.models.oauth_models import (
    TokenResponseModel,
    TokenCreateModel,
    TokenUpdateModel,
    TokenType,
)
from core.helpers.authentication_helper import create_access_token, validate_token
from core.helpers.logger_helper import logger


class TokenService(ITokenService):
    def __init__(self, token_repository: ITokenRepository):
        self.token_repository: ITokenRepository = token_repository

    async def create_access_token(self, token: TokenCreateModel) -> TokenResponseModel:
        # Implement logic to create an access token based on the provided token creation model
        try:
            # Create the access token using the helper function
            access_token: str = create_access_token(data={"sub": token.user_id})
            token.token = access_token
            token.expires_at = self._get_time_to_expire(TokenType.ACCESS)

            # Save the token in the repository (e.g., database)
            await self.token_repository.create_access_token(token)

            # Return the created token as a response model
            return TokenResponseModel(
                access_token=access_token,
                refresh_token=token.parent_token,
                expires_in=self._get_time_to_expire(TokenType.ACCESS),
            )
        except Exception as e:
            logger.error(
                message=f"Error creating access token: {e}",
                error_path="TokenService.create_access_token",
            )
            raise Exception(f"Error creating access token: {e}")

    async def create_refresh_token(self, token: TokenCreateModel) -> TokenResponseModel:
        try:
            refresh_token_str = create_access_token(
                data={"sub": str(token.user_id)}, expires_delta=timedelta(days=7)
            )
            token.token = refresh_token_str
            token.expires_at = self._get_time_to_expire(TokenType.REFRESH)
            token.type = TokenType.REFRESH

            await self.token_repository.create_refresh_token(token)

            return TokenResponseModel(
                access_token="",
                refresh_token=refresh_token_str,
                expires_in=self._get_time_to_expire(TokenType.REFRESH),
            )
        except Exception as e:
            logger.error(
                message=f"Error creating refresh token: {e}",
                error_path="TokenService.create_refresh_token",
            )
            raise Exception(f"Error creating refresh token: {e}")

    async def exchange_access_token(self, access_token: str) -> TokenResponseModel:
        """Exchanges an existing access token for a new set of access and refresh tokens."""
        try:
            # 1. Look up token in DB
            token_model = await self.token_repository.get_token_by_string(access_token)
            if not token_model:
                raise Exception("Invalid access token")

            # 2. Check if revoked and past grace period
            now = datetime.now(timezone.utc)
            if token_model.revoked:
                consumed_at = token_model.consumed_at
                if consumed_at and consumed_at.tzinfo is None:
                    consumed_at = consumed_at.replace(tzinfo=timezone.utc)
                if not consumed_at or now > consumed_at:
                    raise Exception("Access token is fully expired or revoked")
                logger.debug(
                    message=f"Accepting revoked access token {token_model.id} within grace period"
                )
            else:
                # Token is active. We consume it and start the grace period.
                await self.token_repository.revoke_token(token_model)
                logger.debug(
                    message=f"Revoked access token {token_model.id}, starting grace period"
                )

            # 3. Create new access token
            new_access_token_str = create_access_token(
                data={"sub": str(token_model.user_id)}
            )

            # 4. Create new refresh token
            new_refresh_token_str = create_access_token(
                data={"sub": str(token_model.user_id)}, expires_delta=timedelta(days=7)
            )
            new_token_model = TokenCreateModel(
                user_id=token_model.user_id,
                token=new_refresh_token_str,
                type=TokenType.REFRESH,
                parent_token=new_access_token_str,
                expires_at=self._get_time_to_expire(TokenType.REFRESH),
            )
            await self.token_repository.create_refresh_token(new_token_model)

            return TokenResponseModel(
                access_token=new_access_token_str,
                refresh_token=new_refresh_token_str,
                token_type="bearer",
                expires_in=900,
            )
        except Exception as e:
            logger.error(
                message=f"Error exchanging access token: {e}",
                error_path="TokenService.exchange_access_token",
            )
            raise Exception(f"Error exchanging access token: {e}")

    async def exchange_refresh_token(
        self, refresh_token_str: str
    ) -> TokenResponseModel:
        try:
            # 1. Look up token in DB
            token_model = await self.token_repository.get_token_by_string(
                refresh_token_str
            )
            if not token_model:
                raise Exception("Invalid refresh token")

            # 2. Check if revoked and past grace period
            now = datetime.now(timezone.utc)
            if token_model.revoked:
                consumed_at = token_model.consumed_at
                if consumed_at and consumed_at.tzinfo is None:
                    consumed_at = consumed_at.replace(tzinfo=timezone.utc)

                # REUSE DETECTED: If revoked and past grace period
                if not consumed_at or now > consumed_at:
                    await self._handle_security_breach(token_model.user_id)
                    raise Exception(
                        "Refresh token reuse detected. All tokens revoked for security."
                    )

                logger.debug(
                    message=f"Accepting revoked refresh token {token_model.id} within grace period"
                )
            else:
                # Token is active. We consume it and start the grace period.
                await self.token_repository.revoke_token(token_model)
                logger.debug(
                    message=f"Revoked refresh token {token_model.id}, starting grace period"
                )

            # 3. Create new access token
            access_token_str = create_access_token(
                data={"sub": str(token_model.user_id)}
            )

            # 4. Create new refresh token
            new_refresh_token_str = create_access_token(
                data={"sub": str(token_model.user_id)}, expires_delta=timedelta(days=7)
            )
            new_token_model = TokenCreateModel(
                user_id=token_model.user_id,
                token=new_refresh_token_str,
                type=TokenType.REFRESH,
                parent_token=access_token_str,
                expires_at=self._get_time_to_expire(TokenType.REFRESH),
            )
            await self.token_repository.create_refresh_token(new_token_model)

            return TokenResponseModel(
                access_token=access_token_str,
                refresh_token=new_refresh_token_str,
                token_type="bearer",
                expires_in=900,
            )
        except Exception as e:
            logger.error(
                message=f"Error exchanging refresh token: {e}",
                error_path="TokenService.exchange_refresh_token",
            )
            raise Exception(f"Error exchanging refresh token: {e}")

    async def get_last_refresh_token(self, user_id: str) -> TokenResponseModel:
        """Retrieve the last refresh token for the given user ID."""
        try:
            token_model = await self.token_repository.get_last_refresh_token(
                user_id=user_id
            )
            if not token_model:
                raise Exception("Refresh token not found")
            return TokenResponseModel(
                access_token="",  # Access tokens are retrieved separately usually
                refresh_token=token_model.token,
                token_type="bearer",
                expires_in=0,
            )
        except Exception as e:
            logger.error(
                message=f"Error getting last refresh token: {e}",
                error_path="TokenService.get_last_refresh_token",
            )
            raise Exception(f"Error getting last refresh token: {e}")

    async def update(self, token: TokenUpdateModel) -> TokenResponseModel:
        """Update the given token and return the updated token."""
        try:
            # Note: repository update typically takes a TokenUpdateModel and updates by token string
            # This implementation assumes the repository knows how to handle it.
            token_model = await self.token_repository.update(token)
            if not token_model:
                raise Exception("Token not found")
            return TokenResponseModel(
                access_token="",
                refresh_token=token_model.token,
                token_type="bearer",
                expires_in=0,
            )
        except Exception as e:
            logger.error(
                message=f"Error updating token: {e}",
                error_path="TokenService.update",
            )
            raise Exception(f"Error updating token: {e}")

    async def revoke_token(self, token_response: TokenResponseModel) -> None:
        """Revoke the given token."""
        try:
            # We look up the token model by its string first
            token_model = await self.token_repository.get_token_by_string(
                token_response.refresh_token
            )
            if token_model:
                await self.token_repository.revoke_token(token_model)
        except Exception as e:
            logger.error(
                message=f"Error revoking token: {e}",
                error_path="TokenService.revoke_token",
            )
            raise Exception(f"Error revoking token: {e}")

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

    # Private function to validate a token using the helper function
    def _get_time_to_expire(self, type: TokenType) -> datetime:
        if type == TokenType.ACCESS:
            return datetime.now(timezone.utc) + timedelta(minutes=15)
        elif type == TokenType.REFRESH:
            return datetime.now(timezone.utc) + timedelta(days=7)

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
                    return False

            payload = validate_token(refresh_token_str)
            if not payload:
                return False
            return True
        except Exception as e:
            logger.error(
                message=f"Error validating refresh token: {e}",
                error_path="TokenService._validate_refresh_token",
            )
            return False
