from core.models.oauth_models import TokenType
from typing import Any
from typing import List

from core.ports.repository import ITokenRepository
from core.ports.infrastructure import IDatabase
from core.models.oauth_models import TokenModel, TokenCreateModel, TokenUpdateModel
from core.helpers.logger_helper import logger


class InMemoryTokenRepository(ITokenRepository):
    def __init__(self, db: IDatabase):
        self.db: IDatabase = db

    async def create_access_token(self, token: TokenCreateModel) -> TokenModel:
        # Implementation for creating an access token in the database
        try:
            query = """
                INSERT INTO tokens (user_id, token, type, parent_token, expires_at)
                VALUES (%s, %s, %s, %s, %s)
            """
            result: List[dict[str, Any]] = await self.db.execute_with_params(
                query,
                (
                    token.user_id,
                    token.token,
                    token.type.value,
                    token.parent_token,
                    token.expires_at,
                ),
            )
            if not result:
                raise Exception("Failed to create access token")
            token_id: int = await self.db.last_insert_id()
            logger.debug(
                message=f"Access token created with ID: {token_id} for user ID: {token.user_id}"
            )
            return TokenModel(
                id=token_id,
                user_id=token.user_id,
                token=token.token,
                type=token.type,
                parent_token=token.parent_token,
                expires_at=token.expires_at,
            )
        except Exception as e:
            logger.error(
                message=f"Error creating access token: {str(e)}",
                error_path="TokenRepository.create_access_token",
            )
            raise Exception(f"Error creating access token: {str(e)}")

    async def create_refresh_token(self, token: TokenCreateModel) -> TokenModel:
        # Implementation for creating a refresh token in the database
        try:
            query = """
                INSERT INTO tokens (user_id, token, type, expires_at)
                VALUES (%s, %s, %s, %s)
            """
            result: List[dict[str, Any]] = await self.db.execute_with_params(
                query, (token.user_id, token.token, token.type.value, token.expires_at)
            )
            if not result:
                raise Exception("Failed to create refresh token")
            token_id: int = await self.db.last_insert_id()
            logger.debug(
                message=f"Refresh token created with ID: {token_id} for user ID: {token.user_id}"
            )
            return TokenModel(
                id=token_id,
                user_id=token.user_id,
                token=token.token,
                type=token.type,
                parent_token=None,
                expires_at=token.expires_at,
            )
        except Exception as e:
            logger.error(
                message=f"Error creating refresh token: {str(e)}",
                error_path="TokenRepository.create_refresh_token",
            )
            raise Exception(f"Error creating refresh token: {str(e)}")

    async def get_last_refresh_token(self, user_id: str) -> TokenModel:
        # Implementation for retrieving the last refresh token for a user from the database
        try:
            query = """
                SELECT id, user_id, token, type, parent_token, revoked, consumed_at, expires_at, created_at, updated_at FROM tokens
                WHERE user_id = %s AND type = 'refresh'
                ORDER BY created_at DESC
                LIMIT 1
            """
            result: List[dict[str, Any]] = await self.db.execute_with_params(
                query, (user_id,)
            )
            if not result:
                raise Exception("No refresh token found for the user")
            token_data = result[0]
            logger.debug(message=f"Last refresh token retrieved for user ID: {user_id}")
            return TokenModel(
                id=token_data["id"],
                user_id=token_data["user_id"],
                token=token_data["token"],
                type=TokenType(value=token_data["type"]),
                parent_token=token_data.get("parent_token", None),
                revoked=token_data["revoked"],
                consumed_at=token_data.get("consumed_at", None),
                expires_at=token_data["expires_at"],
                created_at=token_data["created_at"],
                updated_at=token_data["updated_at"],
            )
        except Exception as e:
            logger.error(
                message=f"Error retrieving last refresh token: {str(e)}",
                error_path="TokenRepository.get_last_refresh_token",
            )
            raise Exception(f"Error retrieving last refresh token: {str(e)}")

    async def get_token_by_string(self, token: str) -> TokenModel | None:
        try:
            query = """
                SELECT id, user_id, token, type, parent_token, revoked, consumed_at, expires_at, created_at, updated_at FROM tokens
                WHERE token = %s
                LIMIT 1
            """
            result: List[dict[str, Any]] = await self.db.execute_with_params(
                query, (token,)
            )
            if not result:
                return None
            token_data = result[0]
            return TokenModel(
                id=token_data["id"],
                user_id=token_data["user_id"],
                token=token_data["token"],
                type=TokenType(value=token_data["type"]),
                parent_token=token_data.get("parent_token", None),
                revoked=token_data["revoked"],
                consumed_at=token_data.get("consumed_at", None),
                expires_at=token_data["expires_at"],
                created_at=token_data["created_at"],
                updated_at=token_data["updated_at"],
            )
        except Exception as e:
            logger.error(
                message=f"Error retrieving token by string: {str(e)}",
                error_path="TokenRepository.get_token_by_string",
            )
            raise Exception(f"Error retrieving token by string: {str(e)}")

    async def update(self, token: TokenUpdateModel) -> TokenModel:
        # Implementation for updating a token in the database and returning the updated token
        try:
            # First, update the record
            query = """
                UPDATE tokens
                SET revoked = COALESCE(%s, revoked), 
                    consumed_at = COALESCE(%s, consumed_at), 
                    expires_at = COALESCE(%s, expires_at), 
                    updated_at = NOW()
                WHERE token = %s
            """
            await self.db.execute_with_params(
                query, (token.revoked, token.consumed_at, token.expires_at, token.token)
            )

            # Then fetch and return the updated record
            updated_token = await self.get_token_by_string(token.token)
            if not updated_token:
                raise Exception("Token not found after update")

            logger.debug(
                message=f"Token updated: {updated_token.id} for user ID: {updated_token.user_id}"
            )
            return updated_token
        except Exception as e:
            logger.error(
                message=f"Error updating token: {str(e)}",
                error_path="TokenRepository.update",
            )
            raise Exception(f"Error updating token: {str(e)}")

    async def revoke_token(self, token: TokenModel) -> None:
        # Implementation for revoking a token in the database
        try:
            query = """
                UPDATE tokens
                SET revoked = TRUE, consumed_at = NOW() + INTERVAL '30 second', updated_at = NOW()
                WHERE token = %s
            """
            await self.db.execute_with_params(query, (token.token,))
            logger.debug(
                message=f"Token revoked with ID: {token.id} for user ID: {token.user_id}"
            )
        except Exception as e:
            logger.error(
                message=f"Error revoking token: {str(e)}",
                error_path="TokenRepository.revoke_token",
            )
            raise Exception(f"Error revoking token: {str(e)}")

    async def revoke_all_user_tokens(self, user_id: int) -> None:
        # Implementation for revoking all tokens for a user in the database
        try:
            query = """
                UPDATE tokens
                SET revoked = TRUE, consumed_at = NOW(), updated_at = NOW()
                WHERE user_id = %s AND revoked = FALSE
            """
            await self.db.execute_with_params(query, (user_id,))
            logger.debug(message=f"All tokens revoked for user ID: {user_id}")
        except Exception as e:
            logger.error(
                message=f"Error revoking all user tokens: {str(e)}",
                error_path="TokenRepository.revoke_all_user_tokens",
            )
            raise Exception(f"Error revoking all user tokens: {str(e)}")
