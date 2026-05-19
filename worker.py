from arq.connections import RedisSettings
from arq.cron import cron
from core.config.settings import settings
from integration.tasks import sync_all_task
from core.helpers.logger_helper import logger

# Parse INTEGRATION_CRON "minute hour day month weekday"
try:
    cron_parts = settings.INTEGRATION_CRON.split()
    if len(cron_parts) != 5:
        raise ValueError("INTEGRATION_CRON must have 5 parts (m h d M w)")

    m, h, d, month, w = cron_parts

    # ARQ cron expects None for "*"
    cron_kwargs = {
        "minute": int(m) if m != "*" else None,
        "hour": int(h) if h != "*" else None,
        "day": int(d) if d != "*" else None,
        "month": int(month) if month != "*" else None,
        "weekday": int(w) if w != "*" else None,
    }
except Exception as e:
    logger.error(
        f"Error parsing INTEGRATION_CRON '{settings.INTEGRATION_CRON}': {e}. Using default 02:00."
    )
    cron_kwargs = {
        "minute": 0,
        "hour": 2,
        "day": None,
        "month": None,
        "weekday": None,
    }


async def startup(ctx):
    logger.info("Worker starting up...")


async def shutdown(ctx):
    logger.info("Worker shutting down...")


class WorkerSettings:
    """
    ARQ Worker configuration.
    """

    functions = [sync_all_task]
    cron_jobs = [
        cron(
            sync_all_task,
            minute=cron_kwargs["minute"],
            hour=cron_kwargs["hour"],
            day=cron_kwargs["day"],
            month=cron_kwargs["month"],
            weekday=cron_kwargs["weekday"],
            run_at_startup=True,
        )
    ]
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
    )
    on_startup = startup
    on_shutdown = shutdown


if __name__ == "__main__":
    # This block is not strictly necessary as arq worker is usually run via CLI:
    # `arq worker.WorkerSettings`
    pass
