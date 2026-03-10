from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm

from core.util.deps import (
    AuthenticatedUser,
    TokenServiceDeps,
    get_token_from_request,
    get_refresh_token_from_request,
)

from core.models.user_models import UserType
from core.models.oauth_models import (
    ResponseModel,
    TokenRequestModel,
)

from core.helpers.exceptions_helper import (
    SecurityBreachException,
    TokenRevokedException,
    UserNotFoundException,
)

from core.config.settings import settings

oauth_router = APIRouter(
    prefix="/o",
    tags=["OAuth"],
)


@oauth_router.get("/me", response_model=UserType)
async def get_current_user(
    authenticated_user: AuthenticatedUser,
) -> UserType:
    """
    Get the currently authenticated user's information.
    The AuthenticatedUserDeps dependency handles all authentication.
    If the token is invalid, it raises HTTPException(401) automatically
    before this function body ever executes — no try/except needed here.
    """
    return authenticated_user


@oauth_router.post("/refresh", response_model=ResponseModel)
async def refresh_token(
    response: Response,
    service: TokenServiceDeps,
    token_request: TokenRequestModel,
    access_token: Annotated[str | None, Depends(get_token_from_request)] = None,
    refresh_token: Annotated[
        str | None, Depends(get_refresh_token_from_request)
    ] = None,
) -> ResponseModel:
    """Refresh the authentication token for the current user."""
    try:
        final_access_token = access_token
        final_refresh_token = refresh_token

        if not final_access_token or not final_refresh_token:
            raise HTTPException(status_code=401, detail="Tokens missing")

        # Update token_request with found tokens for service call
        token_request.access_token = final_access_token
        token_request.refresh_token = final_refresh_token

        tokens = await service.create_token_pair(token_request)

        # Set new cookies
        response.set_cookie(
            key=settings.COOKIE_ACCESS_TOKEN_NAME,
            value=tokens.access_token,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,  # ty:ignore[invalid-argument-type]
        )
        response.set_cookie(
            key=settings.COOKIE_REFRESH_TOKEN_NAME,
            value=tokens.refresh_token,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,  # ty:ignore[invalid-argument-type]
        )

        return ResponseModel(
            code=200, status="success", message="Token refreshed successfully"
        )
    except SecurityBreachException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except TokenRevokedException as e:
        raise HTTPException(status_code=401, detail=str(e))
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@oauth_router.post("/logout", response_model=ResponseModel)
async def logout(
    response: Response,
    authenticated_user: AuthenticatedUser,
    service: TokenServiceDeps,
    access_token: Annotated[str | None, Depends(get_token_from_request)] = None,
    refresh_token: Annotated[
        str | None, Depends(get_refresh_token_from_request)
    ] = None,
) -> ResponseModel:
    """Log out the current user by invalidating their authentication token."""
    try:
        # Priority: Cookies > Request Body
        final_access_token = access_token
        final_refresh_token = refresh_token

        if not final_access_token or not final_refresh_token:
            raise HTTPException(status_code=401, detail="Tokens missing")

        # Update token_request with found tokens for service call
        token_request = TokenRequestModel(
            user_id=authenticated_user.id,
            access_token=final_access_token,
            refresh_token=final_refresh_token,
        )

        await service.logout(authenticated_user.id, token_request)

        # Delete cookies
        response.delete_cookie(key=settings.COOKIE_ACCESS_TOKEN_NAME)
        response.delete_cookie(key=settings.COOKIE_REFRESH_TOKEN_NAME)

        return ResponseModel(
            code=200, status="success", message="Logged out successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@oauth_router.post("/token/", response_model=ResponseModel, include_in_schema=False)
@oauth_router.post("/token", response_model=ResponseModel)
async def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: TokenServiceDeps,
) -> ResponseModel:
    """
    Authenticate a user and return an authentication token.
    This endpoint is PUBLIC — no authentication required.
    """
    try:
        tokens = await service.login(form_data.username, form_data.password)

        # Set cookies
        response.set_cookie(
            key=settings.COOKIE_ACCESS_TOKEN_NAME,
            value=tokens.access_token,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,  # ty:ignore[invalid-argument-type]
        )
        response.set_cookie(
            key=settings.COOKIE_REFRESH_TOKEN_NAME,
            value=tokens.refresh_token,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,  # ty:ignore[invalid-argument-type]
        )

        return ResponseModel(
            code=200, status="success", message="Logged in successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@oauth_router.post("/token/validate", response_model=ResponseModel)
async def validate_token(
    token_request: TokenRequestModel,
    service: TokenServiceDeps,
    access_token: Annotated[str | None, Depends(get_token_from_request)] = None,
) -> ResponseModel:
    """Validate an authentication token and return the result."""
    try:
        final_access_token = access_token or token_request.access_token
        if not final_access_token:
            raise HTTPException(status_code=401, detail="Token missing")

        is_valid = await service.validate_access_token(final_access_token)
        if is_valid:
            return ResponseModel(code=200, status="success", message="Token is valid")
        else:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
