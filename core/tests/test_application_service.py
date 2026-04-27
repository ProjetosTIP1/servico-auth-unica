import pytest
from datetime import datetime
from core.models.application_models import (
    ApplicationModel,
    ApplicationCreateModel,
    ApplicationType,
)


@pytest.mark.asyncio
async def test_create_application_with_permissions(
    application_service, mock_app_repo, mock_txn
):
    # Setup
    app_create = ApplicationCreateModel(
        name="Perm App",
        uri="https://perm.com",
        type=ApplicationType.INTERNAL,
        permissions=["read", "write", "approve"],
    )

    mock_app_repo.get_application_by_name.return_value = None

    expected_app = ApplicationModel(
        id=1,
        name="Perm App",
        uri="https://perm.com",
        type=ApplicationType.INTERNAL,
        permissions=["read", "write", "approve"],
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_app_repo.create_application.return_value = expected_app

    # Execute
    result = await application_service.create_application(app_create)

    # Verify
    assert result.permissions == ["read", "write", "approve"]
    mock_app_repo.create_application.assert_called_once()


@pytest.mark.asyncio
async def test_get_application_permissions(
    application_service, mock_app_repo, mock_txn
):
    # Setup
    mock_app_repo.get_application_by_id.return_value = ApplicationModel(
        id=1,
        name="Perm App",
        uri="https://perm.com",
        type=ApplicationType.INTERNAL,
        permissions=["read", "write", "approve"],
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Execute
    result = await application_service.get_application_permissions(1)

    # Verify
    assert result == ["read", "write", "approve"]


@pytest.mark.asyncio
async def test_get_application_permissions_empty(
    application_service, mock_app_repo, mock_txn
):
    # Setup
    mock_app_repo.get_application_by_id.return_value = ApplicationModel(
        id=1,
        name="No Perm App",
        uri="https://perm.com",
        type=ApplicationType.INTERNAL,
        permissions=None,
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Execute
    result = await application_service.get_application_permissions(1)

    # Verify
    assert result == []
