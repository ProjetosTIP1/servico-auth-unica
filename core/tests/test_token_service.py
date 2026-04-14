import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from core.models.user_models import UserType
from core.models.oauth_models import TokenType, TokenModel, TokenResponseModel
from core.helpers.exceptions_helper import InvalidCredentialsException


@pytest.mark.asyncio
class TestTokenService:
    @patch("core.services.token_service.verify_password")
    async def test_login_success(
        self, mock_verify, token_service, mock_user_repo, mock_token_repo, mock_txn
    ):
        # Arrange
        mock_verify.return_value = True
        mock_user = UserType(
            id=1,
            username="testuser",
            cpf_cnpj="12345678901",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_repo.get_user_by_cpfcnpj.return_value = mock_user
        mock_user_repo.get_user_hashed_password.return_value = "hashed_password"

        # Act
        result = await token_service.login("12345678901", "password123")

        # Assert
        assert isinstance(result, TokenResponseModel)
        assert result.access_token is not None
        assert result.refresh_token is not None
        mock_token_repo.create_refresh_token.assert_called_once()
        mock_token_repo.create_access_token.assert_called_once()

    @patch("core.services.token_service.verify_password")
    async def test_login_invalid_password_raises_error(
        self, mock_verify, token_service, mock_user_repo
    ):
        # Arrange
        mock_verify.return_value = False
        mock_user = UserType(
            id=1,
            username="testuser",
            cpf_cnpj="12345678901",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_repo.get_user_by_cpfcnpj.return_value = mock_user
        mock_user_repo.get_user_hashed_password.return_value = "hashed_password"

        # Act & Assert
        with pytest.raises(InvalidCredentialsException):
            await token_service.login("12345678901", "wrong_password")

    async def test_logout_success(
        self, token_service, mock_user_repo, mock_token_repo, mock_txn
    ):
        # Arrange
        token_request = MagicMock()
        token_request.access_token = "access_token"
        token_request.refresh_token = "refresh_token"

        mock_user = UserType(
            id=1,
            username="testuser",
            cpf_cnpj="12345678901",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_user_repo.get_user_by_id.return_value = mock_user

        mock_token_model = TokenModel(
            id=1,
            user_id=1,
            token="refresh_token",
            type=TokenType.REFRESH,
            parent_token="",
            revoked=False,
            expires_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_token_repo.get_token_by_string.return_value = mock_token_model

        # Act
        await token_service.logout(1, token_request)

        # Assert
        assert mock_token_repo.revoke_token.call_count == 2
        mock_token_repo.revoke_token.assert_any_call(mock_txn, "refresh_token")
        mock_token_repo.revoke_token.assert_any_call(mock_txn, "access_token")
