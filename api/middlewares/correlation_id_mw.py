"""
Middleware to handle correlation IDs for requests and responses.
It checks for an existing correlation ID in the request headers; if absent, it generates a new one.
It adheres to the Single Responsibility Principle by focusing solely on correlation ID management.
"""

from fastapi import Request
import uuid


async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = str(uuid.uuid4())

    # Add the correlation ID to the request state
    request.state.correlation_id = correlation_id

    # Process the request and get the response
    response = await call_next(request)

    # Add the correlation ID to the response headers
    response.headers["X-Correlation-ID"] = correlation_id

    return response
