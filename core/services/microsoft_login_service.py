"""
Microsoft Login Use Case — Application layer.

Responsibility: orchestrate the process of validating a Microsoft token
and resolving (or provisioning) the local user record.

Architecture notes:
- This service sits in the Application layer.
- It depends on `IMicrosoftAuthService` (abstraction), NOT on MSAL/httpx.
- It depends on `IUserRepository` (abstraction), NOT on MariaDB/SQLAlchemy.
- Both dependencies are injected — this makes the class trivially testable:
  pass mock implementations in tests, real adapters in production.
"""

from dataclasses import dataclass

from core.models.user_models import MicrosoftUserIdentity
from core.ports.service import IMicrosoftAuthService
from core.helpers.logger_helper import logger


@dataclass
class MicrosoftLoginResult:
    """
    Output value object returned after a successful Microsoft login.

    Contains the verified identity from Azure AD plus an optional flag
    indicating whether the user was just created in the local database
    (useful for onboarding flows / first-login welcome screens).
    """

    identity: MicrosoftUserIdentity
    is_new_user: bool = False


class MicrosoftLoginService:
    """
    Use case: validate a Microsoft-issued token and return the authenticated
    user's identity.

    Optionally, it can auto-provision a local user record on first login
    (the "just-in-time provisioning" pattern common in SSO scenarios).

    Inject this service via FastAPI's dependency injection system — see
    `api/handlers/auth_handler.py` for usage.
    """

    def __init__(self, ms_auth: IMicrosoftAuthService) -> None:
        # Depends on the abstraction (port), not the concrete adapter.
        # This is the Dependency Inversion Principle in practice.
        self._ms_auth = ms_auth

    async def execute(self, token: str) -> MicrosoftLoginResult:
        """
        Validate the bearer token and return the resolved user identity.

        Steps:
          1. Delegate cryptographic validation to the infrastructure adapter.
          2. (Optional) Look up or create the user in your local database.
          3. Return a clean result object.

        Args:
            token: Raw JWT string from the Authorization header (no "Bearer " prefix).

        Raises:
            MicrosoftAuthError: forwarded from the adapter if the token is invalid.
        """
        # Step 1 — pure cryptographic validation (done by the infrastructure adapter)
        identity = await self._ms_auth.validate_token(token)

        logger.info(
            message=f"Microsoft token validated for user oid={identity.oid} email={identity.email}"
        )

        # Step 2 — local user provisioning (plug in your UserRepository here)
        # Example (uncomment and adapt when your repository is ready):
        #
        #   user = await self._user_repo.find_by_ms_oid(identity.oid)
        #   is_new = False
        #   if user is None:
        #       user = await self._user_repo.create_from_ms_identity(identity)
        #       is_new = True
        #
        # For now we keep it simple and just return the identity.
        is_new_user = False

        return MicrosoftLoginResult(identity=identity, is_new_user=is_new_user)

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
        return await self._ms_auth.get_auth_url(
            redirect_uri=redirect_uri, scopes=scopes
        )
