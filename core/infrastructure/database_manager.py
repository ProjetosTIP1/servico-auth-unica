"""
Database Connection Manager.

This module provides centralized management of database connections following
Clean Architecture principles. The DatabaseManager acts as an infrastructure
component that handles the lifecycle of all database connections.
"""

from typing import Dict, Any

from core.ports.infrastructure import IDatabase
from core.helpers.logger_helper import logger


class DatabaseManager:
    def __init__(self):
        self._databases: Dict[str, IDatabase] = {}

    @property
    def mariadb(self) -> IDatabase | None:
        """Helper property to get the MariaDB instance."""
        return self._databases.get("mariadb")

    @property
    def sql_server(self) -> IDatabase | None:
        """Helper property to get the SQL Server instance."""
        return self._databases.get("sql_server")

    @property
    def is_initialized(self) -> bool:
        """Check if any database has been registered."""
        return len(self._databases) > 0

    async def initialize(self) -> None:
        """
        Initialize and register all configured databases.
        This follows the 'Factory' pattern to instantiate concrete adapters.
        """
        from core.config.settings import settings
        from core.infrastructure.mariadb_adapter import MariaDbAdapter
        from core.infrastructure.sqls_adapter import SqlServerAdapter

        # Initialize MariaDB
        url: str = settings.database_url
        if url:
            try:
                mariadb = MariaDbAdapter(url)
                await self.register("mariadb", mariadb)
            except Exception as e:
                logger.error(f"Failed to initialize MariaDB: {e}")
        else:
            logger.warning(
                "database_url not configured. MariaDB will not be available."
            )

        # Initialize SQL Server
        sqlserver_url: str = settings.sqlserver_url
        if sqlserver_url:
            try:
                sqls = SqlServerAdapter(sqlserver_url)
                await self.register("sql_server", sqls)
            except Exception as e:
                logger.error(f"Failed to initialize SQL Server: {e}")
        else:
            logger.warning(
                "sqlserver_url not configured. SQL Server will not be available."
            )

    async def register(self, name: str, db: IDatabase) -> None:
        """Register a database connection with a unique name."""
        if name in self._databases:
            logger.warning(f"Database '{name}' is already registered. Overwriting.")
        self._databases[name] = db
        logger.info(f"Database '{name}' registered successfully.")

    async def get(self, name: str) -> IDatabase:
        """Retrieve a registered database connection by name."""
        db: IDatabase | None = self._databases.get(name)
        if not db:
            logger.error(f"Database '{name}' not found.")
            raise ValueError(f"Database '{name}' not registered.")
        return db

    async def shutdown(self) -> None:
        """
        Gracefully close all database connections.

        Handles None connections safely and logs any errors
        without re-raising to ensure all connections are attempted to close.
        """
        logger.info("Closing database connections...")

        for name, db in list(self._databases.items()):
            db: IDatabase | None = db
            if db:
                try:
                    await db.disconnect()
                    logger.info(f"Database '{name}' connection closed.")
                except Exception as e:
                    logger.error(f"Error closing database '{name}' connection: {e}")
            else:
                logger.warning(f"Database '{name}' connection is None, skipping.")

        self._databases.clear()
        logger.info("All database connections closed.")

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of all database connections.

        Returns:
            Dictionary with status for each database:
            {
                "sql_server": {"status": "healthy|unhealthy|not_configured", ...},
                "mariadb": {"status": "healthy|unhealthy|not_configured", ...},
            }
        """
        results: dict[str, Any] = {}

        for name, db in self._databases.items():
            if db:
                try:
                    # Perform a simple query to check connectivity
                    async with db.transaction() as txn:
                        await txn.execute("SELECT 1")
                    results[name] = {"status": "healthy"}
                except Exception as e:
                    logger.error(f"Health check failed for database '{name}': {e}")
                    results[name] = {"status": "unhealthy", "error": str(e)}
            else:
                results[name] = {"status": "not_configured"}
        return results


# Singleton instance - can be replaced with proper DI container later
db_manager = DatabaseManager()
