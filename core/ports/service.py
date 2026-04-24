from core.models.user_models import UserType
from typing import List
from typing import Any
from abc import ABC, abstractmethod

from core.models.oauth_models import (
    TokenResponseModel,
    TokenRequestModel,
    TokenUpdateModel,
)
from core.models.user_models import MicrosoftUserIdentity
from core.models.application_models import (
    ApplicationModel,
    ApplicationCreateModel,
    ApplicationUpdateModel,
    UserApplicationModel,
    UserApplicationCreateModel,
    UserApplicationUpdateModel,
    UserWithPermissionsModel,
)


class ITokenService(ABC):
    """Abstract interface for token service operations"""

    @abstractmethod
    async def create_access_token(self, user: UserType, parent_token: str) -> str:
        """Create a new access token for the given user and parent token."""
        pass

    @abstractmethod
    async def create_refresh_token(self, user: UserType, parent_token: str) -> str:
        """Create a new refresh token for the given user and parent token."""
        pass

    @abstractmethod
    async def create_token_pair(self, token: TokenRequestModel) -> TokenResponseModel:
        """Create a new pair of access and refresh tokens for the given user."""
        pass

    @abstractmethod
    async def get_last_refresh_token(self, user_id: str) -> TokenResponseModel:
        """Retrieve the last refresh token for the given user ID."""
        pass

    @abstractmethod
    async def update(self, token: TokenUpdateModel) -> TokenResponseModel:
        """Update the given token and return the updated token."""
        pass

    @abstractmethod
    async def revoke_token(self, token_response: str) -> None:
        """Revoke the given token."""
        pass

    @abstractmethod
    async def logout(self, auth_user_id: int, token: TokenRequestModel) -> None:
        """Log out the current user by invalidating their authentication tokens."""
        pass

    @abstractmethod
    async def login(self, cpfcnpj: str, password: str) -> TokenResponseModel:
        """Authenticate a user and return an authentication token pair."""
        pass

    @abstractmethod
    async def validate_access_token(self, token: str) -> bool:
        """Validate an access token."""
        pass


class IUserService(ABC):
    """Abstract interface for user service operations"""

    @abstractmethod
    async def get_user_by_cpfcnpj(self, cpf_cnpj: str) -> Any:
        """Get user by CPF/CNPJ"""
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> UserType:
        """Get user by email"""
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> Any:
        """Get user by ID"""
        pass

    @abstractmethod
    async def create_user(self, user_data: Any) -> Any:
        """Create a new user"""
        pass

    @abstractmethod
    async def list_users(self) -> List[Any]:
        """List all users"""
        pass

    @abstractmethod
    async def update_user(self, user_id: int, user_data: Any) -> Any:
        """Update an existing user"""
        pass

    @abstractmethod
    async def update_user_password(self, user_id: int, passwords_data: Any) -> Any:
        """Update the password of an existing user"""
        pass

    @abstractmethod
    async def is_user_admin(self, cpf_cnpj: str) -> bool:
        """Check if the user with the given CPF/CNPJ is an admin"""
        pass

    @abstractmethod
    async def reset_user_password(self, user_email: str, new_password: str) -> None:
        """Reset the password of an existing user"""
        pass

    @abstractmethod
    async def delete_user(self, user_id: int) -> None:
        """Soft delete a user by ID"""
        pass

    @abstractmethod
    async def count_active_users(self) -> int:
        """Count all active users"""
        pass


class IIntegrationService(ABC):
    """Orchestrates the synchronization between SGA and SAM"""

    @abstractmethod
    async def sync_all(self, dry_run: bool = False) -> dict[str, int]:
        """Perform a full synchronization (Departments, Positions, Users)"""
        pass

    @abstractmethod
    async def sync_users(self, dry_run: bool = False) -> dict[str, int]:
        """Synchronize users only"""
        pass

    @abstractmethod
    async def sync_metadata(self, dry_run: bool = False):
        """Synchronize departments and positions only"""
        pass


class IMicrosoftAuthService(ABC):
    """
    Port (interface) for Microsoft / Azure AD token validation.

    Following the Dependency Inversion Principle (DIP), upper layers
    (use cases, FastAPI dependencies) depend on this abstraction, NOT on
    the concrete MSAL or httpx implementation. This makes it trivially
    easy to swap the validator (e.g. mock it in tests).
    """

    @abstractmethod
    async def validate_token(self, token: str) -> MicrosoftUserIdentity:
        """
        Validate a Microsoft-issued JWT (id_token or access_token).

        Steps performed by the concrete adapter:
          1. Fetch Azure AD's public JWKS (cached between calls).
          2. Decode the JWT, verifying signature, expiry, issuer and audience.
          3. Map the verified claims to a `MicrosoftUserIdentity` value object.

        Raises:
            MicrosoftAuthError: if the token is invalid, expired, or untrusted.
        """
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def exchange_code_for_token(
        self, code: str, redirect_uri: str
    ) -> MicrosoftUserIdentity:
        """
        (Optional) Exchange an authorization code for a token and validate it.

        This is only needed if you're implementing the full OAuth flow in the
        backend (e.g. for a CLI tool or server-side rendered app). If your
        frontend uses MSAL.js, it can handle the code exchange itself and you
        don't need this method.

        Args:
            code: The authorization code received from Microsoft after login.
            redirect_uri: The same redirect URI used in the initial auth URL.

        Returns:
            A `MicrosoftUserIdentity` representing the authenticated user.

        Raises:
            MicrosoftAuthError: if the code exchange or token validation fails.
        """
        ...

    @abstractmethod
    async def get_user_profile_picture(self, access_token: str) -> bytes | None:
        """
        Fetch the user's profile picture from Microsoft Graph.

        Args:
            access_token: A valid Microsoft Graph Access Token with 'User.Read' scope.

        Returns:
            The raw bytes of the image, or None if no picture is set or the call fails.
        """
        ...


class IApplicationService(ABC):
    """Abstract interface for application service operations"""

    @abstractmethod
    async def create_application(
        self, app_data: ApplicationCreateModel
    ) -> ApplicationModel:
        """Create a new application"""
        pass

    @abstractmethod
    async def get_application_by_id(self, app_id: int) -> ApplicationModel:
        """Get application by ID"""
        pass

    @abstractmethod
    async def list_applications(self) -> List[ApplicationModel]:
        """List all applications"""
        pass

    @abstractmethod
    async def update_application(
        self, app_id: int, app_data: ApplicationUpdateModel
    ) -> ApplicationModel:
        """Update an existing application"""
        pass

    @abstractmethod
    async def delete_application(self, app_id: int) -> None:
        """Delete an application by ID"""
        pass

    @abstractmethod
    async def link_user_to_application(
        self, link_data: UserApplicationCreateModel
    ) -> UserApplicationModel:
        """Link a user to an application"""
        pass

    @abstractmethod
    async def unlink_user_from_application(self, user_id: int, app_id: int) -> None:
        """Unlink a user from an application"""
        pass

    @abstractmethod
    async def update_user_permissions(
        self, user_id: int, app_id: int, permissions: UserApplicationUpdateModel
    ) -> UserApplicationModel:
        """Update user permissions for a specific application"""
        pass

    @abstractmethod
    async def get_user_permissions(
        self, user_id: int, app_id: int
    ) -> UserApplicationModel:
        """Get user permissions for a specific application"""
        pass

    @abstractmethod
    async def list_user_applications(self, user_id: int) -> List[ApplicationModel]:
        """List all applications linked to a specific user"""
        pass

    @abstractmethod
    async def get_application_users_permissions(
        self, app_id: int
    ) -> List[UserWithPermissionsModel]:
        """Get all users and their permissions for a specific application"""
        pass

    @abstractmethod
    async def get_application_permissions(self, app_id: int) -> List[str]:
        """Get the list of available permissions for an application"""
        pass

    @abstractmethod
    async def check_user_access(self, user_id: int, app_id: int) -> bool:
        """Check if a user has access to an application (manual link or public)"""
        pass
