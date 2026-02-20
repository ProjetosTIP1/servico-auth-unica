from abc import ABC, abstractmethod

from core.models.oauth_models import TokenModel, TokenCreateModel, TokenUpdateModel


class ITokenRepository(ABC):
    @abstractmethod
    async def create_access_token(self, token: TokenCreateModel) -> TokenModel:
        """Create a new access token for the given user information."""
        pass

    @abstractmethod
    async def create_refresh_token(self, token: TokenCreateModel) -> TokenModel:
        """Create a new refresh token for the given user information."""
        pass

    @abstractmethod
    async def get_last_refresh_token(self, user_id: str) -> TokenModel:
        """Retrieve the last refresh token for the given user ID."""
        pass

    @abstractmethod
    async def get_token_by_string(self, token: str) -> TokenModel | None:
        """Retrieve a token by its string value."""
        pass

    @abstractmethod
    async def update(self, token: TokenUpdateModel) -> TokenModel:
        """Update the given token and return the updated token."""
        pass

    @abstractmethod
    async def revoke_token(self, token: TokenModel) -> None:
        """Revoke the given token."""
        pass

    @abstractmethod
    async def revoke_all_user_tokens(self, user_id: int) -> None:
        """Revoke all tokens for the given user ID."""
        pass
