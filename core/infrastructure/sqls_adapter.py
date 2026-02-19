"""
SQL Server Database Adapter.

This module provides a SQL Server implementation of the IDatabase interface,
using asyncio.to_thread() to run synchronous pyodbc operations without
blocking the FastAPI event loop.
"""

import asyncio
from contextlib import contextmanager
from typing import Any

import pyodbc

from core.ports.infrastructure import IDatabase
from core.helpers.logger_helper import logger


class SqlServerAdapter(IDatabase):
    """
    SQL Server database adapter implementing the IDatabase interface.
    
    Uses asyncio.to_thread() to run synchronous pyodbc operations
    without blocking the FastAPI event loop. Connection is reused
    across queries and only closed on application shutdown.
    """
    
    def __init__(self, connection_string: str):
        self._validate_connection_string(connection_string)
        self.connection_string = connection_string
        self._connection: pyodbc.Connection | None = None

    @property
    def connection(self) -> pyodbc.Connection:
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
            self._connection = pyodbc.connect(self.connection_string)
            logger.info("SQL Server connection established successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to SQL Server: {e}")
            raise ConnectionError(f"Failed to connect to SQL Server: {e}")

    def _is_connection_alive_sync(self) -> bool:
        """Check if the current connection is still valid (synchronous)."""
        if self._connection is None:
            return False
        try:
            self._connection.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    @contextmanager
    def _get_cursor(self):
        """
        Context manager for cursor lifecycle.
        Cursor is ALWAYS closed after use, connection remains open.
        """
        cursor = self.connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    async def disconnect(self) -> None:
        """
        Close database connection - call only on shutdown.
        
        This method is safe to call even if connection is None.
        Uses asyncio.to_thread() to avoid blocking.
        """
        if self._connection is None:
            logger.debug("SQL Server connection already closed or never opened.")
            return
        
        def _close():
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error while closing SQL Server connection: {e}")
        
        await asyncio.to_thread(_close)
        self._connection = None
        logger.info("SQL Server connection closed.")

    async def retry_connection(self, retries: int = 3, delay: int = 5) -> bool:
        """Retry database connection with exponential backoff."""
        for attempt in range(retries):
            try:
                await asyncio.to_thread(self._connect_sync)
                return True
            except Exception:
                logger.debug(f"Retrying SQL Server connection (Attempt {attempt + 1} of {retries})...")
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
            with self._get_cursor() as cursor:
                cursor.execute(query)
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
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
            with self._get_cursor() as cursor:
                cursor.execute(query, params)
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                return []
        
        try:
            return await asyncio.to_thread(_execute)
        except Exception as e:
            logger.error(f"Error executing query with params: {e}")
            raise
    
    async def last_insert_id(self) -> int:
        """Get the ID of the last inserted record (for auto-increment primary keys)."""
        def _execute() -> int:
            with self._get_cursor() as cursor:
                cursor.execute("SELECT SCOPE_IDENTITY()")
                result = cursor.fetchone()
                return int(result[0]) if result and result[0] is not None else 0
        
        try:
            return await asyncio.to_thread(_execute)
        except Exception as e:
            logger.error(f"Error fetching last insert ID: {e}")
            raise

    def _validate_connection_string(self, value: str) -> None:
        """Validate connection string format."""
        if not value or value.strip() == "":
            raise ValueError("SQL Server connection string cannot be empty")
        
        required_parts = ['server', 'database']
        connection_lower = value.lower()
        missing_parts = [part for part in required_parts if part not in connection_lower]
        
        if missing_parts:
            raise ValueError(f"Connection string missing required parts: {missing_parts}")