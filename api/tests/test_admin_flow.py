import pytest
from fastapi.testclient import TestClient
from main import app
from core.util.deps import get_user_service, get_token_service
from unittest.mock import AsyncMock, MagicMock

client = TestClient(app)


@pytest.fixture
def mock_services():
    user_service = AsyncMock()
    token_service = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_user_service] = lambda: user_service
    app.dependency_overrides[get_token_service] = lambda: token_service

    yield user_service, token_service

    app.dependency_overrides.clear()


def test_admin_login_success(mock_services):
    user_service, token_service = mock_services

    # Mock token service login
    token_service.login.return_value = MagicMock(
        access_token="fake_access", refresh_token="fake_refresh"
    )

    # Mock user service to return a manager
    user_service.get_user_by_cpfcnpj.return_value = MagicMock(
        cpf_cnpj="123", manager=True
    )

    response = client.post(
        "/admin/login", data={"username": "123", "password": "password"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["redirect_url"] == "/admin/dashboard"
    assert "access_token" in response.cookies


def test_admin_login_forbidden(mock_services):
    user_service, token_service = mock_services

    # Mock token service login
    token_service.login.return_value = MagicMock(
        access_token="fake_access", refresh_token="fake_refresh"
    )

    # Mock user service to return a NON-manager
    user_service.get_user_by_cpfcnpj.return_value = MagicMock(
        cpf_cnpj="456", manager=False
    )

    response = client.post(
        "/admin/login", data={"username": "456", "password": "password"}
    )

    assert response.status_code == 403
    assert "not an admin" in response.json()["detail"]
