from core.models.oauth_models import TokenRequestModel
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from core.util.deps import AuthenticatedUser, TokenServiceDeps

from core.models.user_models import UserType
from core.models.oauth_models import TokenResponseModel, ResponseModel

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


@oauth_router.post("/refresh", response_model=TokenResponseModel)
async def refresh_token(
    authenticated_user: AuthenticatedUser,
    service: TokenServiceDeps,
) -> TokenResponseModel:
    """Refresh the authentication token for the current user."""
    try:
        return await service.refresh_token(authenticated_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@oauth_router.post("/logout", response_model=ResponseModel)
async def logout(
    authenticated_user: AuthenticatedUser,
    service: TokenServiceDeps,
    token: TokenRequestModel,
) -> ResponseModel:
    """Log out the current user by invalidating their authentication token."""
    try:
        await service.logout(authenticated_user.id, token)
        return ResponseModel(
            code=200, status="success", message="Logged out successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@oauth_router.post("/token", response_model=TokenResponseModel)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: TokenServiceDeps,
) -> TokenResponseModel:
    """
    Authenticate a user and return an authentication token.
    This endpoint is PUBLIC — no authentication required.
    """
    try:
        return await service.login(form_data.username, form_data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
