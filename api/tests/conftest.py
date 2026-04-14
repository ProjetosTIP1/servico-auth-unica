import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from main import app
from core.util.deps import get_current_user, get_user_service, get_token_service
from core.models.user_models import UserType
from datetime import datetime, timezone


@pytest.fixture
def mock_user():
    return UserType(
        id=1,
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        manager=True,  # Important for many endpoints
        cpf_cnpj="12345678901",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_user_service():
    return AsyncMock()


@pytest.fixture
def mock_token_service():
    return AsyncMock()


@pytest.fixture
def client(mock_user, mock_user_service, mock_token_service):
    # Dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_token_service] = lambda: mock_token_service

    with TestClient(app) as c:
        yield c

    # Clear overrides after test
    app.dependency_overrides.clear()
