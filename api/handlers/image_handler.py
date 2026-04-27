from fastapi import APIRouter, HTTPException, UploadFile, File
from core.util.deps import AuthenticatedUser, ImageUsecaseDeps, DatabaseDeps
from core.models.oauth_models import ResponseModel

image_router = APIRouter(prefix="/users/me/profile-picture", tags=["Users"])


@image_router.post("", response_model=ResponseModel)
async def upload_profile_picture(
    authenticated_user: AuthenticatedUser,
    service: ImageUsecaseDeps,
    db: DatabaseDeps,
    image: UploadFile = File(...),
) -> ResponseModel:
    """
    Upload a profile picture for the current user.
    """
    try:
        async with db.transaction() as txn:
            await service.upsert_user_profile_picture(
                txn=txn, image=image, user_id=authenticated_user.id
            )

        return ResponseModel(
            code=200, status="success", message="Profile picture updated successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {e}")
