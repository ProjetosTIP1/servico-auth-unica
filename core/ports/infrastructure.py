from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator


class ITransaction(ABC):
    """Represents a single atomic database transaction."""
    
    @abstractmethod
    async def execute(self, query: str, params: dict | None = None) -> list[dict[str, Any]]:
        pass
        
    @abstractmethod
    async def commit(self) -> None:
        pass
        
    @abstractmethod
    async def rollback(self) -> None:
        pass
    
    @abstractmethod
    async def last_insert_id(self) -> int:
        """Get the ID of the last inserted record."""
        pass


class IDatabase(ABC):
    """
    The Connection Pool Manager contract.
    Does NOT execute queries directly. It yields transaction contexts.
    """
    
    @abstractmethod
    def transaction(self) -> AsyncGenerator[ITransaction]:
        """
        Yields an ITransaction. 
        Automatically handles checkout/checkin to the pool.
        """
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        pass
