"""
This module defines context variables for the application.
It uses contextvars to manage request-scoped data like correlation IDs.
"""

from contextvars import ContextVar

# Context variable to store the correlation ID
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id_ctx", default="")


def set_correlation_id(correlation_id: str) -> None:
    """Sets the correlation ID in the current context."""
    correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> str:
    """Retrieves the correlation ID from the current context."""
    return correlation_id_ctx.get()
