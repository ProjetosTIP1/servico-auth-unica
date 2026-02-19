from abc import ABC, abstractmethod
from typing import Any, List


class IDatabase(ABC):
    """
    Abstract interface for database operations.
    
    This interface follows the Interface Segregation Principle (ISP) by exposing
    only the PUBLIC methods that consumers need. Internal implementation details
    like _connect, _get_cursor, etc. are NOT part of the contract.
    
    Note: Methods are async to support non-blocking I/O in FastAPI.
    """
    
    @property
    @abstractmethod
    def connection(self) -> Any:
        """Get or establish database connection (lazy initialization)."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection - call only on application shutdown."""
        pass
    
    @abstractmethod
    async def execute(self, query: str) -> List[dict[str, Any]]:
        """
        Execute a database query and return results.
        
        Args:
            query: SQL query string
            
        Returns:
            List of dictionaries representing query results
        """
        pass
    
    @abstractmethod 
    async def execute_with_params(
        self, query: str, params: tuple | dict[str, Any]
    ) -> List[dict[str, Any]]:
        """
        Execute a parameterized database query (RECOMMENDED for user input).
        This prevents SQL injection attacks.
        
        Args:
            query: SQL query string with parameter placeholders
            params: Tuple or dictionary of parameter values
            
        Returns:
            List of dictionaries representing query results
        """
        pass
    
    @abstractmethod
    async def last_insert_id(self) -> int:
        """Get the ID of the last inserted record (for auto-increment primary keys)."""
        pass