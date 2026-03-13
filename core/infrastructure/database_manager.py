"""
Database Connection Manager.

This module provides centralized management of database connections following
Clean Architecture principles. The DatabaseManager acts as an infrastructure
component that handles the lifecycle of all database connections.
"""

from typing import Dict
from typing import Any

from core.ports.infrastructure import IDatabase

from core.helpers.logger_helper import logger


class DatabaseManager:
    def __init__(self):
        self._databases: Dict[str, IDatabase] = {}

    async def register(self, name: str, db: IDatabase) -> None:
        """Register a database connection with a unique name."""
        if name in self._databases:
            logger.warning(f"Database '{name}' is already registered. Overwriting.")
        self._databases[name] = db
        logger.info(f"Database '{name}' registered successfully.")
    
    async def get(self, name: str) -> IDatabase:
        """Retrieve a registered database connection by name."""
        db = self._databases.get(name)
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

        for name, db in self._databases.items():
            if db:
                try:
                    await db.disconnect()
                    logger.info(f"Database '{name}' connection closed.")
                except Exception as e:
                    logger.error(f"Error closing database '{name}' connection: {e}")
            else:
                logger.warning(f"Database '{name}' connection is None, skipping.")
        
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
                    async for txn in db.transaction():
                        await txn.execute("SELECT 1")
                        break
                    results[name] = {"status": "healthy"}
                except Exception as e:
                    logger.error(f"Health check failed for database '{name}': {e}")
                    results[name] = {"status": "unhealthy", "error": str(e)}
            else:
                logger.warning(f"Database '{name}' is not configured.")
                results[name] = {"status": "not_configured"}
        return results


# Singleton instance - can be replaced with proper DI container later
db_manager = DatabaseManager()
