from core.util.deps import provide_integration_service
from core.helpers.logger_helper import logger

from typing import Any


async def sync_all_task(
    ctx: Any, *args: Any, dry_run: bool = False, **kwargs: Any
) -> Any:
    """
    ARQ task to run the full synchronization process.
    """
    logger.info("Background task: Starting full synchronization...")
    try:
        service = provide_integration_service()
        result = await service.sync_all(dry_run=dry_run)
        logger.info(f"Background task: Synchronization completed. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Background task: Error during synchronization: {str(e)}")
        raise
