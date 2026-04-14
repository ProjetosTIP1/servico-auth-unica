import pytest
from datetime import datetime
from core.models.user_models import UserCreateType, UserType


@pytest.mark.asyncio
class TestUserService:
    async def test_get_user_by_cpfcnpj_success(
        self, user_service, mock_user_repo, mock_txn
    ):
        # Arrange
        mock_user = UserType(
            id=1,
            username="testuser",
            cpf_cnpj="12345678901",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_repo.get_user_by_cpfcnpj.return_value = mock_user

        # Act
        result = await user_service.get_user_by_cpfcnpj("12345678901")

        # Assert
        assert result.cpf_cnpj == "12345678901"
        assert result.id == 1
        mock_user_repo.get_user_by_cpfcnpj.assert_called_once_with(
            mock_txn, "12345678901"
        )

    async def test_get_user_by_cpfcnpj_not_found(self, user_service, mock_user_repo):
        # Arrange
        mock_user_repo.get_user_by_cpfcnpj.return_value = None

        # Act & Assert
        with pytest.raises(Exception, match="User not found"):
            await user_service.get_user_by_cpfcnpj("00000000000")

    async def test_create_user_duplicate_email_raises_error(
        self, user_service, mock_user_repo, mock_txn
    ):
        # Arrange
        user_data = UserCreateType(
            username="newuser",
            cpf_cnpj="11122233344",
            email="duplicate@example.com",
            full_name="Duplicate User",
            password="password123",
        )

        # Mocking existing user by CPF (None) but existing by Email
        mock_user_repo.get_user_by_cpfcnpj.return_value = None
        mock_user_repo.get_user_by_email.return_value = UserType(
            id=2,
            username="existing",
            cpf_cnpj="999",
            email="duplicate@example.com",
            full_name="Existent",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act & Assert
        with pytest.raises(Exception, match="User already exists"):
            await user_service.create_user(user_data)

        mock_user_repo.create_user.assert_not_called()
