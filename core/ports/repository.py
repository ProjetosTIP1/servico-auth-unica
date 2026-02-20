from abc import ABC, abstractmethod

from core.models.oauth_models import TokenModel, TokenCreateModel, TokenUpdateModel, TokenResponseModel

class TokenRepository(ABC):
    @abstractmethod
    async def create_access_token(self, token: TokenCreateModel) -> TokenResponseModel:
        """Create a new access token for the given user information."""
        pass
    
    @abstractmethod
    async def create_refresh_token(self, token: TokenCreateModel) -> TokenResponseModel:
        """Create a new refresh token for the given user information."""
        pass
    
    @abstractmethod
    async def get_last_refresh_token(self, user_id: str) -> TokenResponseModel:
        """Retrieve the last refresh token for the given user ID."""
        pass

    @abstractmethod
    async def update(self, token: TokenUpdateModel) -> TokenModel:
        """Update the given token and return the updated token."""
        pass

    @abstractmethod
    async def revoke_token(self, token: TokenModel) -> None:
        """Revoke the given token."""
        pass