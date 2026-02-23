from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from core.utils.deps import AuthenticatedUserDeps, UserServiceDeps

from core.models.models import ResponseModel, TokenModel, UserModel

oauth_router = APIRouter(
    prefix="/o",
    tags=["OAuth"],
)


@oauth_router.get("/me", response_model=UserModel)
async def get_current_user(
    authenticated_user: AuthenticatedUserDeps,
) -> UserModel:
    """
    Get the currently authenticated user's information.
    The AuthenticatedUserDeps dependency handles all authentication.
    If the token is invalid, it raises HTTPException(401) automatically
    before this function body ever executes — no try/except needed here.
    """
    return authenticated_user


@oauth_router.post("/refresh", response_model=TokenModel)
async def refresh_token(
    authenticated_user: AuthenticatedUserDeps,
    user_service: UserServiceDeps,
) -> TokenModel:
    """Refresh the authentication token for the current user."""
    try:
        return await user_service.refresh_token(authenticated_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@oauth_router.post("/logout", response_model=ResponseModel)
async def logout(
    authenticated_user: AuthenticatedUserDeps,
    user_service: UserServiceDeps,
) -> ResponseModel:
    """Log out the current user by invalidating their authentication token."""
    try:
        await user_service.logout(authenticated_user)
        return ResponseModel(
            code=200, status="success", message="Logged out successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@oauth_router.post("/token", response_model=TokenModel)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserServiceDeps,
) -> TokenModel:
    """
    Authenticate a user and return an authentication token.
    This endpoint is PUBLIC — no authentication required.
    """
    try:
        return await user_service.login(form_data.username, form_data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
