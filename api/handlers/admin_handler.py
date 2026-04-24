from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from core.util.deps import (
    AuthenticatedUser,
    TokenServiceDeps,
    UserServiceDeps,
    get_current_user_optional,
)
from core.models.oauth_models import ResponseModel
from core.config.settings import settings

# Setup templates
templates = Jinja2Templates(directory="templates")

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


@admin_router.get("/login", response_class=HTMLResponse)
async def get_admin_login(
    request: Request,
    user: Annotated[
        AuthenticatedUser | None, Depends(get_current_user_optional)
    ] = None,
):
    """Render the admin login page."""
    if user and user.manager:
        return RedirectResponse(url="/admin/dashboard")
    return templates.TemplateResponse("admin_login.html", {"request": request})


@admin_router.post("/login")
async def admin_login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    token_service: TokenServiceDeps,
    user_service: UserServiceDeps,
):
    """
    Authenticate an admin.
    Returns JSON with redirect info for the frontend.
    """
    try:
        # 1. Standard login to verify credentials
        tokens = await token_service.login(form_data.username, form_data.password)

        # 2. Check if the user is a manager
        user = await user_service.get_user_by_cpfcnpj(form_data.username)
        if not user.manager:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: User is not an admin",
            )

        # 3. Set cookies
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
            code=200,
            status="success",
            message="Admin logged in successfully",
            data={"redirect_url": "/admin/dashboard"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Invalid credentials or access denied: {e}"
        )


@admin_router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    authenticated_user: AuthenticatedUser,
):
    """
    Render the SAM Admin Dashboard.
    """
    if not authenticated_user.manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You must be a manager to access this page",
        )

    return templates.TemplateResponse(
        "admin_dashboard.html", {"request": request, "user": authenticated_user}
    )
