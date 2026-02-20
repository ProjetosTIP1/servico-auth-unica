from fastapi import FastAPI

from api.handlers.auth_handler import ms_router
from api.middlewares.correlation_id_mw import correlation_id_middleware

app = FastAPI()

# Register middleware
app.middleware(middleware_type="http")(correlation_id_middleware)

# Register routers
app.include_router(router=ms_router, prefix="/ms", tags=["Microsoft"])
