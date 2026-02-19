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
