import pytest
from core.models.oauth_models import TokenResponseModel
from datetime import datetime, timezone


@pytest.mark.asyncio
class TestUserAPI:
    async def test_get_user_by_id_success(self, client, mock_user_service, mock_user):
        # Arrange
        mock_user_service.get_user_by_id.return_value = mock_user

        # Act
        response = client.get("/users/1")

        # Assert
        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert response.json()["username"] == "admin"

    async def test_create_user_success(self, client, mock_user_service, mock_user):
        # Arrange
        mock_user_service.create_user.return_value = mock_user
        user_payload = {
            "username": "newuser",
            "email": "new@example.com",
            "cpf_cnpj": "11122233344",
            "full_name": "New User",
            "password": "password123",
        }

        # Act
        response = client.post("/users/", json=user_payload)

        # Assert
        assert (
            response.status_code == 200
        )  # Handlers return 200 on success in this project
        assert response.json()["username"] == "admin"  # Returning mocked success user


@pytest.mark.asyncio
class TestAuthAPI:
    async def test_login_success(self, client, mock_token_service):
        # Arrange
        mock_token_service.login.return_value = TokenResponseModel(
            access_token="fake_access",
            refresh_token="fake_refresh",
            expires_in=datetime.now(timezone.utc),
        )
        login_data = {"username": "admin", "password": "password123"}

        # Act
        response = client.post("/o/token", data=login_data)

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Logged in successfully"
        # Verify cookies
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert response.cookies["access_token"] == "fake_access"
