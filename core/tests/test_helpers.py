from datetime import datetime, timedelta
from core.helpers.authentication_helper import (
    get_password_hash,
    verify_password,
    create_jwt_token,
    validate_token,
)
from core.helpers.datetime_helper import (
    get_current_date_context_helper,
    current_day_formatted,
)


class TestAuthenticationHelper:
    def test_password_hashing_and_verification(self):
        # Arrange
        password = "secure_password_123"

        # Act
        hashed = get_password_hash(password)
        is_valid = verify_password(password, hashed)
        is_invalid = verify_password("wrong_password", hashed)

        # Assert
        assert hashed != password
        assert is_valid is True
        assert is_invalid is False

    def test_jwt_token_creation_and_validation(self):
        # Arrange
        payload = {"sub": "12345678901", "name": "Test User"}

        # Act
        token = create_jwt_token(payload, expires_delta=timedelta(minutes=10))
        decoded_payload = validate_token(token)

        # Assert
        assert token is not None
        assert decoded_payload["sub"] == "12345678901"
        assert decoded_payload["name"] == "Test User"
        assert decoded_payload["type"] == "access"

    def test_invalid_token_validation(self):
        # Act
        decoded = validate_token("invalid.token.string")

        # Assert
        assert decoded is None


class TestDatetimeHelper:
    def test_get_current_date_context_helper_structure(self):
        # Act
        context = get_current_date_context_helper()

        # Assert
        expected_keys = [
            "current_date_str",
            "current_date_iso",
            "last_week_start",
            "last_week_end",
            "current_month",
            "current_year",
            "last_month",
            "last_month_iso",
        ]
        for key in expected_keys:
            assert key in context

        # Verify ISO format for current_date_iso
        datetime.strptime(context["current_date_iso"], "%Y-%m-%d")

    def test_current_day_formatted(self):
        # Act
        today_str = current_day_formatted()

        # Assert
        # Matches YYYY-MM-DD
        assert len(today_str) == 10
        datetime.strptime(today_str, "%Y-%m-%d")
