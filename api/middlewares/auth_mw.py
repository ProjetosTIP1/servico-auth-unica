"""
This middleware module handles authentication for incoming requests to authenticated endpoints.
It verifies JWT tokens and attaches the authenticated user information to the request state.
It adheres to the Single Responsibility Principle by focusing solely on authentication logic.
"""

from core.helpers.authentication_helper import validate_token
from fastapi import Request


async def auth_middleware(request: Request, call_next):
    try:
        token = request.headers.get("Authorization")
        if token:
            token = token.replace("Bearer ", "")
            payload = validate_token(token)
            if payload:
                request.state.user = payload.get("sub")
            else:
                request.state.user = None
        else:
            request.state.user = None

        response = await call_next(request)
        return response
    except Exception as e:
        print(f"Error in authentication middleware: {e}")
        raise e
