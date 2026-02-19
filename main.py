"""
Microsoft MSAL — quick demo & mental model for this microservice.

Run with:
    python main.py

This file is NOT the FastAPI app entry point (that will be app.py or similar).
Its purpose is to illustrate three distinct MSAL scenarios so you understand
which one applies to your architecture:

  SCENARIO A — Interactive login (NOT what a backend microservice does)
    PublicClientApplication: the app itself drives the login flow.
    Used in CLI tools, desktop apps.  Your backend NEVER does this.

  SCENARIO B — Backend acquires a token for a downstream service
    ConfidentialClientApplication with client-credentials or on-behalf-of.
    Used when YOUR backend calls another API (e.g. Microsoft Graph) on the
    user's behalf.  Optional for this project.

  SCENARIO C ✅ — Backend VALIDATES an incoming token (what we actually do)
    The frontend already acquired the token via MSAL.js.  Your backend only
    needs to verify the JWT signature and claims using Azure AD's public keys.
    No MSAL needed at all — just python-jose + HTTPS GET to the JWKS endpoint.
    This is what `MicrosoftAuthAdapter` in core/infrastructure/ implements.
"""

import asyncio
import os

from core.infrastructure.microsoft_auth_adapter import (
    MicrosoftAuthAdapter,
    MicrosoftAuthError,
)


async def demo_validate_token(token: str) -> None:
    """
    SCENARIO C — validate an already-obtained Microsoft JWT.

    Replace `token` with a real id_token from:
      - Azure Portal > your app > Overview > "Test sign-in"
      - Or grab it from MSAL.js in your frontend (window.__msal_token)
    """
    adapter = MicrosoftAuthAdapter()

    try:
        identity = await adapter.validate_token(token)
        print("   Token is valid!")
        print(f"    OID    : {identity.oid}")
        print(f"    Email  : {identity.email}")
        print(f"    Name   : {identity.name}")
        print(f"    Tenant : {identity.tenant_id}")
        print(f"    Roles  : {identity.roles}")
    except MicrosoftAuthError as exc:
        print(f"❌  Token validation failed: {exc}")


async def main() -> None:
    # Replace this with a real token for an actual test.
    sample_token = os.getenv("MS_TEST_TOKEN", "paste-a-real-ms-token-here")

    print("=" * 60)
    print("SCENARIO C: validating an incoming Microsoft JWT")
    print("=" * 60)
    await demo_validate_token(sample_token)

    print()
    print("Next steps:")
    print("  1. Set AZURE_TENANT_ID and AZURE_CLIENT_ID in your .env file")
    print("  2. Obtain a real id_token from your frontend (MSAL.js) or")
    print("     Azure Portal test tool, and set MS_TEST_TOKEN=<token>")
    print("  3. Run `uvicorn app:app --reload` and call POST /auth/microsoft/validate")


if __name__ == "__main__":
    asyncio.run(main())

