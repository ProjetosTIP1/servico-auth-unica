from typing import List
from fastapi import APIRouter, HTTPException
from core.util.deps import AuthenticatedUser, ApplicationServiceDeps
from core.models.oauth_models import ResponseModel
from core.models.application_models import (
    ApplicationModel,
    ApplicationCreateModel,
    ApplicationUpdateModel,
    UserApplicationModel,
    UserApplicationCreateModel,
    UserWithPermissionsModel,
)

application_router = APIRouter(prefix="/applications", tags=["Applications"])


@application_router.get("/", response_model=List[ApplicationModel])
async def list_applications(
    authenticated_user: AuthenticatedUser,
    service: ApplicationServiceDeps,
):
    """List all applications. Only accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return await service.list_applications()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.post("/", response_model=ApplicationModel)
async def create_application(
    authenticated_user: AuthenticatedUser,
    app_data: ApplicationCreateModel,
    service: ApplicationServiceDeps,
):
    """Create a new application. Only accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return await service.create_application(app_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.get("/{app_id}", response_model=ApplicationModel)
async def get_application(
    authenticated_user: AuthenticatedUser,
    app_id: int,
    service: ApplicationServiceDeps,
):
    """Get an application by ID."""
    try:
        app = await service.get_application_by_id(app_id)
        if not authenticated_user.manager and not app.is_active:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return app
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.patch("/{app_id}", response_model=ApplicationModel)
async def update_application(
    authenticated_user: AuthenticatedUser,
    app_id: int,
    app_data: ApplicationUpdateModel,
    service: ApplicationServiceDeps,
):
    """Update an application. Only accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return await service.update_application(app_id, app_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.delete("/{app_id}", response_model=ResponseModel)
async def delete_application(
    authenticated_user: AuthenticatedUser,
    app_id: int,
    service: ApplicationServiceDeps,
):
    """Delete an application. Only accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        await service.delete_application(app_id)
        return ResponseModel(
            code=200, status="success", message="Application deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.post("/link", response_model=UserApplicationModel)
async def link_user_to_application(
    authenticated_user: AuthenticatedUser,
    link_data: UserApplicationCreateModel,
    service: ApplicationServiceDeps,
):
    """Link a user to an application with permissions. Only accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return await service.link_user_to_application(link_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@application_router.post("/{app_id}/users/bulk-link")
async def bulk_link_users(
    authenticated_user: AuthenticatedUser,
    app_id: int,
    service: ApplicationServiceDeps,
    search: str = "",
):
    """Link all users (optionally filtered by search) to an application. Only accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        await service.bulk_link_users(app_id, search)
        return {"message": "Users linked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.delete("/{app_id}/users/bulk-unlink")
async def bulk_unlink_users(
    authenticated_user: AuthenticatedUser,
    app_id: int,
    service: ApplicationServiceDeps,
):
    """Unlink all users from an application. Only accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        await service.bulk_unlink_users(app_id)
        return {"message": "Users unlinked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.delete("/{app_id}/users/{user_id}", response_model=ResponseModel)
async def unlink_user_from_application(
    authenticated_user: AuthenticatedUser,
    app_id: int,
    user_id: int,
    service: ApplicationServiceDeps,
):
    """Unlink a user from an application. Only accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        await service.unlink_user_from_application(user_id, app_id)
        return ResponseModel(
            code=200, status="success", message="User unlinked successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.get(
    "/{app_id}/users", response_model=List[UserWithPermissionsModel]
)
async def list_application_users(
    authenticated_user: AuthenticatedUser,
    app_id: int,
    service: ApplicationServiceDeps,
):
    """List all users and their permissions for an application. Only accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return await service.get_application_users_permissions(app_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.get("/{app_id}/permissions", response_model=List[str])
async def list_application_permissions(
    authenticated_user: AuthenticatedUser,
    app_id: int,
    service: ApplicationServiceDeps,
):
    """List all available permissions for an application. Accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return await service.get_application_permissions(app_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.get("/user/{user_id}", response_model=List[ApplicationModel])
async def list_user_applications(
    authenticated_user: AuthenticatedUser,
    user_id: int,
    service: ApplicationServiceDeps,
):
    """List all applications for a specific user. Users can only see their own list unless they are managers."""
    try:
        if not authenticated_user.manager and authenticated_user.id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return await service.list_user_applications(user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@application_router.get(
    "/{app_id}/available-users", response_model=List[UserWithPermissionsModel]
)
async def list_available_users(
    authenticated_user: AuthenticatedUser,
    app_id: int,
    service: ApplicationServiceDeps,
    search: str = "",
):
    """List all active users NOT linked to an application, with optional search filtering. Only accessible by managers."""
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return await service.get_available_users(app_id, search)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


