"""
SQL Server Database Adapter.

This module provides a SQL Server implementation of the IDatabase interface,
using asyncio.to_thread() to run synchronous pyodbc operations without
blocking the FastAPI event loop.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import pyodbc

from core.ports.infrastructure import IDatabase, ITransaction
from core.helpers.logger_helper import logger


class SqlServerTransaction(ITransaction):
    def __init__(self, connection: pyodbc.Connection):
        self._conn = connection

    async def execute(
        self, query: str, params: dict | None = None
    ) -> list[dict[str, Any]]:
        def _execute() -> list[dict[str, Any]]:
            cursor = self._conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                return []
            finally:
                cursor.close()

        try:
            return await asyncio.to_thread(_execute)
        except pyodbc.Error as e:
            logger.error(
                f"Database execution error: {e}.\nQuery: {query}\nParams: {params}"
            )
            raise

    async def commit(self) -> None:
        await asyncio.to_thread(self._conn.commit)

    async def rollback(self) -> None:
        await asyncio.to_thread(self._conn.rollback)

    async def last_insert_id(self) -> int:
        def _execute() -> int:
            cursor = self._conn.cursor()
            try:
                cursor.execute("SELECT SCOPE_IDENTITY()")
                result = cursor.fetchone()
                return int(result[0]) if result and result[0] is not None else 0
            finally:
                cursor.close()

        return await asyncio.to_thread(_execute)


class SqlServerAdapter(IDatabase):
    """
    SQL Server database adapter implementing the IDatabase interface.

    Uses asyncio.to_thread() to run synchronous pyodbc operations
    without blocking the FastAPI event loop. A connection is opened
    per transaction and returned to pyodbc's internal ODBC pool after use.
    """

    def __init__(self, connection_string: str):
        self._validate_connection_string(connection_string)
        self._connection_string = connection_string
        logger.info("SqlServerAdapter initialized.")

    def _open_connection_sync(self) -> pyodbc.Connection:
        try:
            return pyodbc.connect(self._connection_string, autocommit=False)
        except Exception as e:
            logger.error(f"Failed to connect to SQL Server: {e}")
            raise ConnectionError(f"Failed to connect to SQL Server: {e}")

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[ITransaction, None]:
        """
        1. Opens a connection (from pyodbc's internal ODBC pool).
        2. Yields the ITransaction interface.
        3. Commits on success, rolls back on exception.
        4. Returns the connection to the pool.
        """
        conn = await asyncio.to_thread(self._open_connection_sync)
        transaction_impl = SqlServerTransaction(conn)
        try:
            yield transaction_impl
            await transaction_impl.commit()
        except Exception as e:
            logger.error(f"Transaction failed, rolling back: {e}")
            await transaction_impl.rollback()
            raise
        finally:
            await asyncio.to_thread(conn.close)

    async def disconnect(self) -> None:
        # pyodbc manages its own internal ODBC connection pool; nothing to dispose.
        logger.info("SqlServerAdapter: no persistent pool to dispose.")

    def _validate_connection_string(self, value: str) -> None:
        if not value or value.strip() == "":
            raise ValueError("SQL Server connection string cannot be empty")

        required_parts = ["server", "database"]
        missing_parts = [p for p in required_parts if p not in value.lower()]
        if missing_parts:
            raise ValueError(
                f"Connection string missing required parts: {missing_parts}"
            )
