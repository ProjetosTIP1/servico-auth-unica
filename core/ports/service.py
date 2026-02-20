from abc import ABC, abstractmethod
from core.models.user_models import MicrosoftUserIdentity


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
