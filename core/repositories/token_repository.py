from core.models.oauth_models import TokenType

from core.ports.repository import ITokenRepository
from core.ports.infrastructure import ITransaction
from core.models.oauth_models import TokenModel, TokenCreateModel, TokenUpdateModel
from core.helpers.logger_helper import logger


class TokenRepository(ITokenRepository):
    async def create_access_token(
        self, txn: ITransaction, token: TokenCreateModel
    ) -> TokenModel:
        """Create an access token record in the database."""
        try:
            query = """
                INSERT INTO tokens (user_id, token, type, parent_token, expires_at, created_at, updated_at)
                VALUES (:user_id, :token, :type, :parent_token, :expires_at, NOW(), NOW())
            """
            await txn.execute(
                query,
                {
                    "user_id": token.user_id,
                    "token": token.token,
                    "type": token.type.value,
                    "parent_token": token.parent_token,
                    "expires_at": token.expires_at,
                },
            )
            logger.debug(message=f"Access token created for user ID: {token.user_id}")
            token_res: TokenModel | None = await self.get_token_by_string(
                txn, token.token
            )
            if not token_res:
                raise Exception("Token not found after creation")
            return token_res
        except Exception as e:
            logger.error(
                message=f"Error creating access token: {str(e)}",
                error_path="TokenRepository.create_access_token",
            )
            raise Exception(f"Error creating access token: {str(e)}")

    async def create_refresh_token(
        self, txn: ITransaction, token: TokenCreateModel
    ) -> TokenModel:
        """Create a refresh token record in the database."""
        try:
            query = """
                INSERT INTO tokens (user_id, token, type, parent_token, expires_at, created_at, updated_at)
                VALUES (:user_id, :token, :type, :parent_token, :expires_at, NOW(), NOW())
            """
            await txn.execute(
                query,
                {
                    "user_id": token.user_id,
                    "token": token.token,
                    "type": token.type.value,
                    "parent_token": token.parent_token,
                    "expires_at": token.expires_at,
                },
            )
            logger.debug(message=f"Refresh token created for user ID: {token.user_id}")
            token_res: TokenModel | None = await self.get_token_by_string(
                txn, token.token
            )
            if not token_res:
                raise Exception("Token not found after creation")
            return token_res
        except Exception as e:
            logger.error(
                message=f"Error creating refresh token: {str(e)}",
                error_path="TokenRepository.create_refresh_token",
            )
            raise Exception(f"Error creating refresh token: {str(e)}")

    async def get_last_refresh_token(
        self, txn: ITransaction, user_id: str
    ) -> TokenModel:
        """Retrieve the most recent refresh token for a user."""
        try:
            query = """
                SELECT id, user_id, token, type, parent_token, revoked, consumed_at, expires_at, created_at, updated_at
                FROM tokens
                WHERE user_id = :user_id AND type = 'refresh'
                ORDER BY created_at DESC
                LIMIT 1
            """
            result = await txn.execute(query, {"user_id": user_id})
            if not result:
                raise Exception("No refresh token found for the user")
            token_data = result[0]
            logger.debug(message=f"Last refresh token retrieved for user ID: {user_id}")
            return TokenModel(
                id=token_data["id"],
                user_id=token_data["user_id"],
                token=token_data["token"],
                type=TokenType(value=token_data["type"]),
                parent_token=str(token_data.get("parent_token")),
                revoked=token_data["revoked"],
                consumed_at=token_data.get("consumed_at"),
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

    async def get_token_by_string(
        self, txn: ITransaction, token: str
    ) -> TokenModel | None:
        """Retrieve a token by its JWT string value."""
        try:
            query = """
                SELECT id, user_id, token, type, parent_token, revoked, consumed_at, expires_at, created_at, updated_at
                FROM tokens
                WHERE token = :token
                LIMIT 1
            """
            result = await txn.execute(query, {"token": token})
            if not result:
                return None
            token_data = result[0]
            return TokenModel(
                id=token_data["id"],
                user_id=token_data["user_id"],
                token=token_data["token"],
                type=TokenType(value=token_data["type"]),
                parent_token=str(token_data.get("parent_token")),
                revoked=token_data["revoked"],
                consumed_at=token_data.get("consumed_at"),
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

    async def update(self, txn: ITransaction, token: TokenUpdateModel) -> TokenModel:
        """Update a token's revoked/consumed/expires fields."""
        try:
            query = """
                UPDATE tokens
                SET revoked = COALESCE(:revoked, revoked),
                    consumed_at = COALESCE(:consumed_at, consumed_at),
                    expires_at = COALESCE(:expires_at, expires_at),
                    updated_at = NOW()
                WHERE token = :token
            """
            await txn.execute(
                query,
                {
                    "revoked": token.revoked,
                    "consumed_at": token.consumed_at,
                    "expires_at": token.expires_at,
                    "token": token.token,
                },
            )
            updated_token = await self.get_token_by_string(txn, token.token)
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

    async def revoke_token(self, txn: ITransaction, token: str) -> None:
        """Mark a token as revoked, with a 30-second grace period."""
        try:
            query = """
                UPDATE tokens
                SET revoked = TRUE,
                    consumed_at = DATE_ADD(NOW(), INTERVAL 30 SECOND),
                    updated_at = NOW()
                WHERE token = :token
            """
            await txn.execute(query, {"token": token})
            logger.debug(message=f"Token revoked with ID: {token[:10]}...")
        except Exception as e:
            logger.error(
                message=f"Error revoking token: {str(e)}",
                error_path="TokenRepository.revoke_token",
            )
            raise Exception(f"Error revoking token: {str(e)}")

    async def revoke_all_user_tokens(self, txn: ITransaction, user_id: int) -> None:
        """Revoke all active tokens for a given user (security breach response)."""
        try:
            query = """
                UPDATE tokens
                SET revoked = TRUE, consumed_at = NOW(), updated_at = NOW()
                WHERE user_id = :user_id AND revoked = FALSE
            """
            await txn.execute(query, {"user_id": user_id})
            logger.debug(message=f"All tokens revoked for user ID: {user_id}")
        except Exception as e:
            logger.error(
                message=f"Error revoking all user tokens: {str(e)}",
                error_path="TokenRepository.revoke_all_user_tokens",
            )
            raise Exception(f"Error revoking all user tokens: {str(e)}")
