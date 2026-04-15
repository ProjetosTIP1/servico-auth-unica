from fastapi import APIRouter, HTTPException

from core.util.deps import AuthenticatedUser, UserServiceDeps

from core.models.oauth_models import ResponseModel
from core.models.user_models import (
    UserCreateType,
    UserUpdateType,
    UserUpdatePasswordType,
    UserType,
)

user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.get("/{user_id}", response_model=UserType)
async def get_user_by_id(
    authenticated_user: AuthenticatedUser, user_id: int, user_service: UserServiceDeps
):
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        user: UserType = await user_service.get_user_by_id(user_id)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/cpfcnpj/{cpf_cnpj}", response_model=UserType)
async def get_user_by_cpfcnpj(
    authenticated_user: AuthenticatedUser, cpf_cnpj: str, user_service: UserServiceDeps
):
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        user: UserType = await user_service.get_user_by_cpfcnpj(cpf_cnpj)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/list", response_model=list[UserType])
async def get_all_users(
    authenticated_user: AuthenticatedUser, user_service: UserServiceDeps
):
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        users: list[UserType] = await user_service.list_users()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post("/", response_model=UserType)
async def create_user(
    authenticated_user: AuthenticatedUser,
    user_data: UserCreateType,
    user_service: UserServiceDeps,
):
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        user: UserType = await user_service.create_user(user_data)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.patch("/{user_id}", response_model=UserType)
async def update_user(
    authenticated_user: AuthenticatedUser,
    user_id: int,
    user_data: UserUpdateType,
    user_service: UserServiceDeps,
):
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        user: UserType = await user_service.update_user(user_id, user_data)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.patch("/{user_id}/password", response_model=ResponseModel)
async def update_user_password(
    authenticated_user: AuthenticatedUser,
    user_id: int,
    user_data: UserUpdatePasswordType,
    user_service: UserServiceDeps,
):
    try:
        if not authenticated_user:
            raise HTTPException(status_code=403, detail="Unauthorized")
        await user_service.update_user_password(user_id, user_data)
        return ResponseModel(
            code=200,
            message="User password updated successfully",
            status="success",
            data=None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.patch("/{user_email}/reset-password", response_model=ResponseModel)
async def reset_user_password(
    user_email: str,
    new_password: str,
    user_service: UserServiceDeps,
):
    try:
        await user_service.reset_user_password(user_email, new_password)
        return ResponseModel(
            code=200,
            message="User password reset successfully",
            status="success",
            data=None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.delete("/{user_id}", response_model=ResponseModel)
async def delete_user(
    authenticated_user: AuthenticatedUser, user_id: int, user_service: UserServiceDeps
):
    try:
        if not authenticated_user.manager:
            raise HTTPException(status_code=403, detail="Unauthorized")
        await user_service.delete_user(user_id)
        return ResponseModel(
            code=200, message="User deleted successfully", status="success", data=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post("/is-admin", response_model=ResponseModel)
async def is_admin(
    cpf_cnpj: str,
    service: UserServiceDeps,
) -> ResponseModel:
    """Check if the user with the given CPF/CNPJ is an admin."""
    try:
        is_admin: bool = await service.is_user_admin(cpf_cnpj)
        return ResponseModel(
            code=200,
            status="success",
            message="User is admin" if is_admin else "User is not admin",
            data={"is_admin": is_admin},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
