from fastapi import FastAPI

from api.handlers.auth_handler import ms_router
from api.handlers.oauth_handler import oauth_router

from api.middlewares.correlation_id_mw import correlation_id_middleware
from api.middlewares.auth_mw import auth_middleware

app = FastAPI()

# Register middleware
app.middleware(middleware_type="http")(correlation_id_middleware)
app.middleware(middleware_type="http")(auth_middleware)

# Register routers
app.include_router(router=ms_router, prefix="/ms", tags=["Microsoft"])
app.include_router(router=oauth_router, prefix="/oauth", tags=["OAuth"])
