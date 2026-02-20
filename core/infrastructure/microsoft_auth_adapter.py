"""
Microsoft / Azure token validation adapter.

This is the ONLY file in the codebase that knows about MSAL, JWKS, or
the exact shape of Azure JWT claims. Everything above this layer
(services, handlers) works with clean domain types.

Architecture note (DIP):
  This class implements `IMicrosoftAuthService` (the port).
  It lives in the Infrastructure layer, which means it is allowed to depend
  on external libraries (msal, jose, httpx). The layers above it MUST NOT.
"""

from msal import ConfidentialClientApplication
import time
from typing import Any

import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from core.config.settings import settings
from core.models.user_models import MicrosoftUserIdentity
from core.ports.service import IMicrosoftAuthService
from core.helpers.logger_helper import logger

# How long to cache the JWKS keys before re-fetching (in seconds).
_JWKS_CACHE_TTL = 3600  # 1 hour


class MicrosoftAuthError(Exception):
    """Raised when Microsoft token validation fails for any reason."""


class MicrosoftAuthAdapter(IMicrosoftAuthService):
    """
    Validates Microsoft-issued JWTs (id_token or access_token) against
    Azure AD's public JWKS endpoint.

    Why no MSAL for validation?
    ---
    MSAL shines when your app needs to *acquire* tokens (interactive login,
    on-behalf-of, client-credentials).  For *validating* tokens sent by a
    client, the standard approach is:
        1. Fetch the JWKS from Azure AD's well-known endpoint.
        2. Verify the JWT signature with python-jose.
        3. Assert the expected claims (issuer, audience, expiry).

    This keeps the adapter stateless and dependency-light: no MSAL session,
    no browser redirects — just pure cryptographic verification.
    """

    def __init__(self) -> None:
        # JWKS in-memory cache: avoids a network round-trip on every request.
        self._jwks_cache: dict[str, Any] = {}
        self._cache_fetched_at: float = 0.0
        self._provider = ConfidentialClientApplication(
            client_id=settings.AZURE_CLIENT_ID,
            client_credential=settings.AZURE_CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}",
        )

    # ── Public interface (implements IMicrosoftAuthService) ────────────────────

    async def validate_token(self, token: str) -> MicrosoftUserIdentity:
        """
        Validate the JWT and return a clean `MicrosoftUserIdentity`.

        Raises:
            MicrosoftAuthError: for any validation failure (expired, bad sig, etc.)
        """
        jwks = await self._get_jwks()

        try:
            # python-jose resolves the correct key from the JWKS automatically
            # using the `kid` header in the token.
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                # audience = your Azure app's client ID (or "api://<client_id>")
                audience=settings.AZURE_CLIENT_ID,
                # Allow tokens from your tenant OR multi-tenant ("common")
                options={"verify_aud": bool(settings.AZURE_CLIENT_ID)},
            )
        except ExpiredSignatureError:
            raise MicrosoftAuthError("Token has expired.")
        except JWTClaimsError as exc:
            raise MicrosoftAuthError(f"Token claims are invalid: {exc}")
        except JWTError as exc:
            raise MicrosoftAuthError(f"Token signature verification failed: {exc}")

        return self._map_claims_to_identity(payload)

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
        # This method is left unimplemented for now since the frontend uses MSAL.js,
        # which can construct the URL itself. If you want to implement this, you can
        # use MSAL's PublicClientApplication.get_authorization_request_url() method.
        try:
            auth_url: str = self._provider.get_authorization_request_url(
                scopes=scopes,
                redirect_uri=redirect_uri,
            )
            return auth_url
        except Exception as exc:
            raise MicrosoftAuthError(
                f"Failed to generate Microsoft auth URL: {exc}"
            ) from exc

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
        # This method is left unimplemented for now since the frontend uses MSAL.js,
        # which can handle the code exchange itself. If you want to implement this,
        # you can use MSAL's ConfidentialClientApplication.acquire_token_by_authorization_code() method.
        try:
            result = self._provider.acquire_token_by_authorization_code(
                code=code,
                scopes=[f"{settings.AZURE_CLIENT_ID}/.default"],
                redirect_uri=redirect_uri,
            )
            if "access_token" in result:
                return await self.validate_token(result["access_token"])
            else:
                raise MicrosoftAuthError(
                    f"Failed to acquire token: {result.get('error_description', 'Unknown error')}"
                )
        except Exception as exc:
            raise MicrosoftAuthError(
                f"Failed to exchange code for token: {exc}"
            ) from exc

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _get_jwks(self) -> dict[str, Any]:
        """
        Return the cached JWKS, re-fetching from Azure AD if the TTL has elapsed.

        Azure AD rotates its signing keys periodically, so we cache for 1 hour
        and refresh on expiry instead of hitting the network on every request.
        """
        now = time.monotonic()
        if self._jwks_cache and (now - self._cache_fetched_at) < _JWKS_CACHE_TTL:
            return self._jwks_cache

        logger.info(message=f"Fetching Azure AD JWKS from {settings.azure_jwks_uri}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(settings.azure_jwks_uri)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._cache_fetched_at = now
        except httpx.HTTPError as exc:
            raise MicrosoftAuthError(
                f"Failed to fetch Azure AD public keys: {exc}"
            ) from exc

        return self._jwks_cache

    @staticmethod
    def _map_claims_to_identity(claims: dict[str, Any]) -> MicrosoftUserIdentity:
        """
        Map raw JWT claim names to our clean domain model.

        Azure AD claim reference:
          https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference
        """
        # `oid` is the stable, immutable user ID within Azure AD.
        oid = claims.get("oid") or claims.get("sub")
        if not oid:
            raise MicrosoftAuthError("Token is missing the 'oid' / 'sub' claim.")

        # Email can come from different claims depending on token type / config.
        email = (
            claims.get("email")
            or claims.get("preferred_username")
            or claims.get("upn")
            or ""
        )
        if not email:
            raise MicrosoftAuthError("Token is missing an email / upn claim.")

        return MicrosoftUserIdentity(
            oid=oid,
            email=email,
            name=claims.get("name"),
            given_name=claims.get("given_name"),
            family_name=claims.get("family_name"),
            tenant_id=claims.get("tid"),
            preferred_username=claims.get("preferred_username"),
            roles=claims.get("roles", []),
        )
