import pytest
import polars as pl
from unittest.mock import MagicMock
from integration.integration_service import IntegrationService
from core.ports.repository import ISgaRepository, ISamIntegrationRepository


@pytest.fixture
def mock_sga_repo():
    return MagicMock(spec=ISgaRepository)


@pytest.fixture
def mock_sam_repo():
    return MagicMock(spec=ISamIntegrationRepository)


@pytest.fixture
def integration_service(mock_sga_repo, mock_sam_repo):
    return IntegrationService(sga_repo=mock_sga_repo, sam_repo=mock_sam_repo)


@pytest.fixture
def sam_schema():
    return {
        "username": pl.String,
        "nome_completo": pl.String,
        "is_active": pl.Int64,
        "unidade": pl.String,
        "cargo": pl.String,
        "departamento": pl.String,
    }


@pytest.mark.asyncio
async def test_sync_users_new_user_detection(
    integration_service, mock_sga_repo, mock_sam_repo, sam_schema
):
    # Setup: 1 new user in SGA, 0 in SAM
    sga_df = pl.DataFrame(
        {
            "username": ["123.456.789-00"],  # Needs cleaning
            "nome_completo": ["New User"],
            "cargo": ["Dev"],
            "departamento": ["IT"],
            "unidade": ["UnitA"],
        }
    )
    sam_df = pl.DataFrame(schema=sam_schema)

    mock_sga_repo.get_users_df.return_value = sga_df
    mock_sga_repo.get_disabled_users_df.return_value = pl.DataFrame()
    mock_sam_repo.get_current_users_df.return_value = sam_df
    mock_sam_repo.upsert_users.return_value = 1

    # Execute
    await integration_service.sync_users(dry_run=False)

    # Verify
    args, _ = mock_sam_repo.upsert_users.call_args
    upserted_df = args[0]
    assert upserted_df.height == 1
    assert upserted_df["username"][0] == "12345678900"
    assert "password" in upserted_df.columns


@pytest.mark.asyncio
async def test_sync_users_update_detection(
    integration_service, mock_sga_repo, mock_sam_repo, sam_schema
):
    # Setup: User exists in both but name changed in SGA
    sga_df = pl.DataFrame(
        {
            "username": ["admin"],
            "nome_completo": ["Admin Updated"],
            "cargo": ["Dev"],
            "departamento": ["IT"],
            "unidade": ["UnitA"],
        }
    )
    sam_df = pl.DataFrame(
        {
            "username": ["admin"],
            "nome_completo": ["Admin Old"],
            "is_active": [1],
            "unidade": ["UnitA"],
            "cargo": ["Dev"],
            "departamento": ["IT"],
        }
    )

    mock_sga_repo.get_users_df.return_value = sga_df
    mock_sga_repo.get_disabled_users_df.return_value = pl.DataFrame()
    mock_sam_repo.get_current_users_df.return_value = sam_df
    mock_sam_repo.upsert_users.return_value = 1

    # Execute
    await integration_service.sync_users(dry_run=False)

    # Verify
    mock_sam_repo.upsert_users.assert_called_once()
    args, _ = mock_sam_repo.upsert_users.call_args
    upserted_df = args[0]
    assert upserted_df.height == 1
    assert upserted_df["nome_completo"][0] == "Admin Updated"


@pytest.mark.asyncio
async def test_sync_users_disabled_detection(
    integration_service, mock_sga_repo, mock_sam_repo, sam_schema
):
    # Setup: Active user in SAM is now in disabled list from SGA
    mock_sga_repo.get_users_df.return_value = (
        pl.DataFrame()
    )  # No active in SGA for this test

    disabled_df = pl.DataFrame({"username": ["former_employee"]})
    sam_df = pl.DataFrame(
        {
            "username": ["former_employee"],
            "nome_completo": ["Old User"],
            "is_active": [1],  # Currently active
            "unidade": ["UnitA"],
            "cargo": ["Dev"],
            "departamento": ["IT"],
        }
    )

    mock_sga_repo.get_disabled_users_df.return_value = disabled_df
    mock_sam_repo.get_current_users_df.return_value = sam_df
    mock_sam_repo.disable_users.return_value = 1

    # Execute
    await integration_service.sync_users(dry_run=False)

    # Verify
    mock_sam_repo.disable_users.assert_called_once_with(["former_employee"])


@pytest.mark.asyncio
async def test_sync_users_dry_run(
    integration_service, mock_sga_repo, mock_sam_repo, sam_schema
):
    # Setup
    sga_df = pl.DataFrame(
        {
            "username": ["new"],
            "nome_completo": ["New"],
            "cargo": ["X"],
            "departamento": ["Y"],
            "unidade": ["Z"],
        }
    )
    mock_sga_repo.get_users_df.return_value = sga_df
    mock_sga_repo.get_disabled_users_df.return_value = pl.DataFrame()
    mock_sam_repo.get_current_users_df.return_value = pl.DataFrame(schema=sam_schema)

    # Execute with dry_run=True
    await integration_service.sync_users(dry_run=True)

    # Verify: No write methods called
    mock_sam_repo.upsert_users.assert_not_called()
    mock_sam_repo.disable_users.assert_not_called()
