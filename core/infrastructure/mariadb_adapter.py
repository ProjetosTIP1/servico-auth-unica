"""
MariaDB Database Adapter.

This module provides a MariaDB implementation of the IDatabase interface,
using SQLAlchemy's connection pooling for efficient connection management
and asyncio.to_thread() to run synchronous operations without blocking.
"""

import asyncio
from typing import Any

from sqlalchemy import Connection, Engine, create_engine, text

from core.ports.infrastructure import IDatabase
from core.helpers.logger_helper import logger


class MariaDbAdapter(IDatabase):
    """
    MariaDB database adapter implementing the IDatabase interface.

    Uses SQLAlchemy's connection pooling with asyncio.to_thread() to run
    synchronous operations without blocking the FastAPI event loop.
    Connection is reused across queries and only closed on application shutdown.
    """

    def __init__(self, connection_string: str):
        self._validate_connection_string(connection_string)
        self.connection_string = connection_string
        self._engine: Engine | None = None

    def _ensure_engine(self) -> Engine:
        """Ensures the engine is initialized once."""
        if self._engine is None:
            self._engine = create_engine(
                self.connection_string,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Validates connections before use
                pool_recycle=3600,  # Recycle connections every hour
            )
            logger.info("MariaDB Engine initialized.")
        return self._engine

    @property
    def connection(self) -> Connection:
        """
        Lazy connection initialization with automatic reconnection.

        Returns the existing connection or creates a new one if needed.
        This is a synchronous property - use execute() for async operations.
        """
        if self._connection is None or not self._is_connection_alive_sync():
            self._connect_sync()
        return self._connection

    def _connect_sync(self) -> None:
        """Establish database connection (synchronous)."""
        try:
            if self._engine is None:
                self._engine = create_engine(
                    self.connection_string,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,  # Validates connections before use
                    pool_recycle=3600,  # Recycle connections every hour
                    echo=False,  # Set to True for SQL logging in development
                )
            self._connection = self._engine.connect()
            logger.info("MariaDB connection established successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to MariaDB: {e}")
            raise ConnectionError(f"Failed to connect to MariaDB: {e}")

    def _is_connection_alive_sync(self) -> bool:
        """Check if the current connection is still valid (synchronous)."""
        if self._connection is None:
            return False
        try:
            row = self._connection.execute(text("SELECT 1")).fetchone()
            if row is None or row[0] != 1:
                logger.warning("MariaDB connection check failed: Unexpected result")
                return False
            return True
        except Exception as e:
            logger.warning(f"MariaDB connection check failed: {e}")
            return False

    async def disconnect(self) -> None:
        """
        Close database connection - call only on shutdown.

        This method is safe to call even if connection is None.
        Uses asyncio.to_thread() to avoid blocking.
        """
        if self._connection is None:
            logger.debug("MariaDB connection already closed or never opened.")
            return

        def _close():
            try:
                self._connection.close()
                if self._engine:
                    self._engine.dispose()
            except Exception as e:
                logger.warning(f"Error while closing MariaDB connection: {e}")

        await asyncio.to_thread(_close)
        self._connection = None
        self._engine = None
        logger.info("MariaDB connection closed.")

    async def retry_connection(self, retries: int = 3, delay: int = 5) -> bool:
        """Retry database connection with exponential backoff."""
        for attempt in range(retries):
            try:
                await asyncio.to_thread(self._connect_sync)
                return True
            except Exception:
                logger.debug(
                    f"Retrying MariaDB connection (Attempt {attempt + 1} of {retries})..."
                )
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
        return False

    async def execute(self, query: str) -> list[dict[str, Any]]:
        """
        Execute a database query and return results.

        Uses asyncio.to_thread() to avoid blocking the event loop.

        Args:
            query: SQL query string

        Returns:
            List of dictionaries representing query results
        """

        def _execute() -> list[dict[str, Any]]:
            engine = self._ensure_engine()
            # Context manager ensures connection is returned to the pool
            with engine.connect() as conn:
                result = conn.execute(text(query))
                conn.commit()
                if result.returns_rows:
                    columns = result.keys()
                    return [dict(zip(columns, row)) for row in result.fetchall()]
                return []

        try:
            return await asyncio.to_thread(_execute)
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    async def execute_with_params(
        self, query: str, params: tuple | dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Execute a parameterized database query (prevents SQL injection).

        Uses asyncio.to_thread() to avoid blocking the event loop.

        Args:
            query: SQL query string with parameter placeholders
            params: Tuple or dictionary of parameter values

        Returns:
            List of dictionaries representing query results
        """

        def _execute() -> list[dict[str, Any]]:
            engine = self._ensure_engine()
            # Context manager ensures connection is returned to the pool
            with engine.connect() as conn:
                result = conn.execute(text(query), params)
                conn.commit()
                if result.returns_rows:
                    columns = result.keys()
                    return [dict(zip(columns, row)) for row in result.fetchall()]
                return []

        try:
            return await asyncio.to_thread(_execute)
        except Exception as e:
            logger.error(f"Error executing query with params: {e}")
            raise

    async def last_insert_id(self) -> int:
        """Get the ID of the last inserted record (for auto-increment primary keys)."""
        engine = self._ensure_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT LAST_INSERT_ID()"))
            return result.scalar()

    def _validate_connection_string(self, connection_string: str) -> None:
        """Basic validation for the connection string format."""
        if not connection_string.startswith("mariadb"):
            raise ValueError(
                "Invalid connection string format. Must start with 'mariadb://'."
            )
