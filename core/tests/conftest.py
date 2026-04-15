import pytest
from unittest.mock import AsyncMock, MagicMock
from core.ports.infrastructure import IDatabase, ITransaction
from core.repositories.user_repository import IUserRepository
from core.repositories.token_repository import ITokenRepository
from core.services.user_service import UserService
from core.services.token_service import TokenService


@pytest.fixture
def mock_txn():
    """Returns a mock transaction."""
    txn = AsyncMock(spec=ITransaction)
    return txn


@pytest.fixture
def mock_db(mock_txn):
    """Returns a mock database manager that yields a mock transaction."""
    db = MagicMock(spec=IDatabase)

    # Mock the async context manager 'transaction'
    class AsyncContextManagerMock:
        async def __aenter__(self):
            return mock_txn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    db.transaction.return_value = AsyncContextManagerMock()
    return db


@pytest.fixture
def mock_user_repo():
    """Returns a mock user repository."""
    return AsyncMock(spec=IUserRepository)


@pytest.fixture
def mock_token_repo():
    """Returns a mock token repository."""
    return AsyncMock(spec=ITokenRepository)


@pytest.fixture
def user_service(mock_user_repo, mock_db):
    """Returns a UserService instance with mocked dependencies."""
    return UserService(user_repository=mock_user_repo, db=mock_db)


@pytest.fixture
def token_service(mock_token_repo, mock_user_repo, mock_db):
    """Returns a TokenService instance with mocked dependencies."""
    return TokenService(
        token_repository=mock_token_repo, user_repository=mock_user_repo, db=mock_db
    )
