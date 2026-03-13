from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.handlers.oauth_handler import oauth_router
from api.handlers.user_handler import user_router
from api.handlers.ms_handler import ms_router
from api.handlers.integration_handler import router as integration_router


from core.infrastructure.database_manager import db_manager, DatabaseManager

from api.middlewares.correlation_id_mw import correlation_id_middleware

from core.helpers.logger_helper import logger

from core.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await db_manager.initialize()
        status = await db_manager.health_check()
        if not status:
            logger.error("Database health check failed. Check connection settings.")
            raise ConnectionError("Failed to connect to database.")
        app.state.db_manager: DatabaseManager = db_manager
        logger.info("Database connection established.")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
    except KeyboardInterrupt:
        await db_manager.shutdown()
        logger.info("Shutdown signal received. Database connection closed.")

    yield
    # Shutdown
    await db_manager.shutdown()
    logger.info("Database connection closed.")


app = FastAPI(
    title="Single Auth Microservice",
    description="Single Auth Microservice",
    version="1.0.0",
    lifespan=lifespan,
)
# Register middleware
app.middleware(middleware_type="http")(correlation_id_middleware)

# Register CORS middleware
app.add_middleware(
    CORSMiddleware,  # ty:ignore[invalid-argument-type]
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(router=oauth_router, tags=["OAuth"])
app.include_router(router=user_router, tags=["Users"])
app.include_router(router=ms_router)
app.include_router(router=integration_router)
