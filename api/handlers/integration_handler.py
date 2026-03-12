from fastapi import APIRouter, Depends, HTTPException, status
from core.ports.service import IIntegrationService
from core.util.deps import get_integration_service

router = APIRouter(prefix="/integration", tags=["Integration"])

@router.post("/sync-all", status_code=status.HTTP_200_OK)
async def sync_all(
    dry_run: bool = False,
    service: IIntegrationService = Depends(get_integration_service)
):
    """
    Perform a full synchronization between SGA and SAM.
    - Dry run will only log the changes without applying them.
    """
    try:
        await service.sync_all(dry_run=dry_run)
        return {"message": "Full synchronization completed successfully", "dry_run": dry_run}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during full synchronization: {e}"
        )

@router.post("/sync-users", status_code=status.HTTP_200_OK)
async def sync_users(
    dry_run: bool = False,
    service: IIntegrationService = Depends(get_integration_service)
):
    """
    Synchronize users only.
    """
    try:
        await service.sync_users(dry_run=dry_run)
        return {"message": "User synchronization completed successfully", "dry_run": dry_run}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during user synchronization: {e}"
        )

@router.post("/sync-metadata", status_code=status.HTTP_200_OK)
async def sync_metadata(
    dry_run: bool = False,
    service: IIntegrationService = Depends(get_integration_service)
):
    """
    Synchronize metadata (Departments and Positions) only.
    """
    try:
        await service.sync_metadata(dry_run=dry_run)
        return {"message": "Metadata synchronization completed successfully", "dry_run": dry_run}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during metadata synchronization: {e}"
        )
