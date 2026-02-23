from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.handlers.oauth_handler import oauth_router

from core.infrastructure.database_manager import db_manager

from api.middlewares.correlation_id_mw import correlation_id_middleware
from api.middlewares.auth_mw import auth_middleware

from core.helpers.logger_helper import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await db_manager.initialize()
        app.state.db_manager = db_manager
        logger.info("Database connection established.")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
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
app.middleware(middleware_type="http")(auth_middleware)

# Register routers
app.include_router(router=oauth_router, tags=["OAuth"])
