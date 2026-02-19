"""
Database Connection Manager.

This module provides centralized management of database connections following
Clean Architecture principles. The DatabaseManager acts as an infrastructure
component that handles the lifecycle of all database connections.
"""

from dataclasses import dataclass

from core.ports.infrastructure import IDatabase
from core.infrastructure.mariadb_adapter import MariaDbAdapter
from core.infrastructure.sqls_adapter import SqlServerAdapter
from core.config.settings import settings
from core.helpers.logger_helper import logger



@dataclass
class DatabaseConnections:
    """Container for all database connections."""
    sql_server: IDatabase | None = None
    mariadb: IDatabase | None = None
    mariadb_ramal_table: IDatabase | None = None  # Assuming same connection can be used for all tables, but can be extended if needed


class DatabaseManager:
    """
    Manages database connection lifecycle.
    
    This follows SRP by isolating connection management from the FastAPI app,
    and DIP by depending on the IDatabase interface, not concrete implementations.
    
    Usage:
        manager = DatabaseManager()
        await manager.initialize()
        # Use manager.sql_server or manager.mariadb
        await manager.shutdown()
    """
    
    def __init__(self):
        self._connections = DatabaseConnections()
        self._initialized = False
    
    @property
    def sql_server(self) -> IDatabase | None:
        """Get SQL Server database connection."""
        return self._connections.sql_server
    
    @property
    def mariadb(self) -> IDatabase | None:
        """Get MariaDB database connection."""
        return self._connections.mariadb
    
    @property
    def mariadb_ramal_table(self) -> IDatabase | None:
        """Get MariaDB connection specifically for the ramal table."""
        return self._connections.mariadb_ramal_table  # Assuming same connection can be used for all tables
    
    @property
    def is_initialized(self) -> bool:
        """Check if the manager has been initialized."""
        return self._initialized

    async def initialize(self) -> None:
        """
        Initialize all database connections.
        
        Logs errors but continues initialization of other databases.
        This allows partial functionality if one database is unavailable.
        """
        logger.info("Initializing database connections...")
        errors: list[str] = []
        
        # SQL Server
        try:
            sql_server_db = SqlServerAdapter(settings.sqlserver_url)
            await sql_server_db.execute("SELECT 1")  # Validate connection
            self._connections.sql_server = sql_server_db
            logger.info("SQL Server connection initialized successfully.")
        except Exception as e:
            error_msg = f"SQL Server initialization failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # MariaDB
        try:
            mariadb_db = MariaDbAdapter(settings.database_url)
            await mariadb_db.execute("SELECT 1")  # Validate connection
            self._connections.mariadb = mariadb_db
            logger.info("MariaDB connection initialized successfully.")
        except Exception as e:
            error_msg = f"MariaDB initialization failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # MariaDB Ramal Table
        try:
            mariadb_ramal_table_db = MariaDbAdapter(settings.database_url_ramal)
            await mariadb_ramal_table_db.execute("SELECT 1")  # Validate connection
            self._connections.mariadb_ramal_table = mariadb_ramal_table_db
            logger.info("MariaDB Ramal Table connection initialized successfully.")
        except Exception as e:
            error_msg = f"MariaDB Ramal Table initialization failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        if errors:
            logger.warning(f"Some database connections failed: {errors}")
        
        self._initialized = True

    async def shutdown(self) -> None:
        """
        Gracefully close all database connections.
        
        Handles None connections safely and logs any errors
        without re-raising to ensure all connections are attempted to close.
        """
        logger.info("Closing database connections...")
        
        if self._connections.sql_server:
            try:
                await self._connections.sql_server.disconnect()
                logger.info("SQL Server connection closed.")
            except Exception as e:
                logger.error(f"Error closing SQL Server connection: {e}")
        
        if self._connections.mariadb:
            try:
                await self._connections.mariadb.disconnect()
                logger.info("MariaDB connection closed.")
            except Exception as e:
                logger.error(f"Error closing MariaDB connection: {e}")
        
        if self._connections.mariadb_ramal_table:
            try:
                await self._connections.mariadb_ramal_table.disconnect()
                logger.info("MariaDB Ramal Table connection closed.")
            except Exception as e:
                logger.error(f"Error closing MariaDB Ramal Table connection: {e}")
        
        self._connections = DatabaseConnections()
        self._initialized = False
        logger.info("All database connections closed.")

    async def health_check(self) -> dict[str, any]:
        """
        Check health of all database connections.
        
        Returns:
            Dictionary with status for each database:
            {
                "sql_server": {"status": "healthy|unhealthy|not_configured", ...},
                "mariadb": {"status": "healthy|unhealthy|not_configured", ...},
                "mariadb_ramal_table": {"status": "healthy|unhealthy|not_configured", ...}
            }
        """
        results: dict[str, any] = {}
        
        # SQL Server health check
        if self._connections.sql_server:
            try:
                await self._connections.sql_server.execute("SELECT 1")
                results["sql_server"] = {"status": "healthy", "connected": True}
            except Exception as e:
                results["sql_server"] = {"status": "unhealthy", "error": str(e)}
        else:
            results["sql_server"] = {"status": "not_configured", "connected": False}
        
        # MariaDB health check
        if self._connections.mariadb:
            try:
                await self._connections.mariadb.execute("SELECT 1")
                results["mariadb"] = {"status": "healthy", "connected": True}
            except Exception as e:
                results["mariadb"] = {"status": "unhealthy", "error": str(e)}
        else:
            results["mariadb"] = {"status": "not_configured", "connected": False}
        
        # MariaDB Ramal Table health check
        if self._connections.mariadb_ramal_table:
            try:
                await self._connections.mariadb_ramal_table.execute("SELECT 1")
                results["mariadb_ramal_table"] = {"status": "healthy", "connected": True}
            except Exception as e:
                results["mariadb_ramal_table"] = {"status": "unhealthy", "error": str(e)}
        else:
            results["mariadb_ramal_table"] = {"status": "not_configured", "connected": False}
        
        return results


# Singleton instance - can be replaced with proper DI container later
db_manager = DatabaseManager()
