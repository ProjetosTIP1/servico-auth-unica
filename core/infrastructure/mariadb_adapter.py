"""
MariaDB Database Adapter.

This module provides a MariaDB implementation of the IDatabase interface,
using SQLAlchemy's connection pooling for efficient connection management
and asyncio.to_thread() to run synchronous operations without blocking.
"""
from fastapi.concurrency import asynccontextmanager

from typing import Any
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from core.ports.infrastructure import IDatabase, ITransaction
from core.helpers.logger_helper import logger

from core.config.settings import settings


class MariaDbTransaction(ITransaction):
    def __init__(self, connection: AsyncConnection):
        self._conn: AsyncConnection = connection
    
    async def execute(self, query: str, params: dict | None = None) -> list[dict[str, Any]]:
        try:
            result = await self._conn.execute(text(query), params or {})
            if result.returns_rows:
                return [dict(row._mapping) for row in result.all()]
            return []
        except SQLAlchemyError as e:
            logger.error(f"Database execution error: {e}.\nQuery: {query}\nParams: {params}")
            raise
    
    async def commit(self) -> None:
        await self._conn.commit()
    
    async def rollback(self) -> None:
        await self._conn.rollback()
    
    async def last_insert_id(self) -> int:
        result = await self._conn.execute(text("SELECT LAST_INSERT_ID()"))
        return result.scalar_one() or 0


class MariaDbAdapter(IDatabase):
    """
    MariaDB database adapter implementing the IDatabase interface.

    Uses SQLAlchemy's connection pooling with asyncio.to_thread() to run
    synchronous operations without blocking the FastAPI event loop.
    Connection is reused across queries and only closed on application shutdown.
    """

    def __init__(self, connection_string: str):
        self._validate_connection_string(connection_string)
        
        self._engine: AsyncEngine = create_async_engine(
            connection_string,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Validates connections before use
            pool_recycle=3600,  # Recycle connections every hour
            echo=settings.DEVELOPMENT_ENV,  # Set to True for SQL logging in development
        )
        logger.info("MariaDB Engine initialized.")
    
    def _validate_connection_string(self, connection_string: str) -> None:
        if not connection_string.startswith("mariadb+"):
            raise ValueError(
                "Invalid connection string. For async operations, "
                "use a driver prefix like 'mariadb+asyncmy://' or 'mariadb+aiomysql://'."
            )

    @asynccontextmanager
    async def transaction(self) -> AbstractAsyncContextManager[ITransaction]:
        """
        The magic happens here. 
        1. Borrows a connection from the pool.
        2. Starts a transaction (begin).
        3. Yields the ITransaction interface.
        4. Automatically commits if successful, or rolls back if an exception occurs.
        5. Returns the connection to the pool.
        """
        async with self._engine.connect() as conn:
            async with conn.begin():
                transaction_impl = MariaDbTransaction(conn)
                try:
                    yield transaction_impl
                    # conn.begin() automatically commits upon successful exit of this block
                except Exception as e:
                    logger.error(f"Transaction failed, rolling back: {e}")
                    # conn.begin() automatically rolls back upon exception
                    raise

    async def disconnect(self) -> None:
        if self._engine:
            await self._engine.dispose()
            logger.info("MariaDB Engine disposed, all connections closed.")