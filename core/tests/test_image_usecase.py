import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
import os
from io import BytesIO
from core.services.image_usecase import ImageUsecase, MAX_FILE_SIZE

@pytest.fixture
def image_usecase():
    return ImageUsecase()

@pytest.fixture
def mock_upload_file():
    """Returns a mock UploadFile with content."""
    content = b"fake image content"
    file_obj = BytesIO(content)
    
    # Mocking the FastAPI UploadFile
    mock_file = MagicMock(spec=UploadFile)
    mock_file.file = file_obj
    mock_file.read = AsyncMock(side_effect=lambda size=-1: file_obj.read(size))
    mock_file.seek = AsyncMock(side_effect=file_obj.seek)
    
    return mock_file

@pytest.mark.asyncio
class TestImageUsecase:
    
    @patch("core.services.image_usecase.filetype.guess")
    @patch("core.services.image_usecase.uuid4")
    @patch("core.services.image_usecase.aiofiles.open")
    @patch("core.services.image_usecase.os.makedirs")
    async def test_upsert_user_profile_picture_success(
        self, mock_makedirs, mock_open, mock_uuid, mock_guess, 
        image_usecase, mock_upload_file, mock_txn
    ):
        # Arrange
        user_id = 1
        mock_uuid.return_value.hex = "fakeuuid"
        
        # Mocking filetype detection
        mock_kind = MagicMock()
        mock_kind.mime = "image/jpeg"
        mock_kind.extension = "jpg"
        mock_guess.return_value = mock_kind
        
        # Mocking aiofiles context manager
        mock_file_context = AsyncMock()
        mock_open.return_value.__aenter__.return_value = mock_file_context

        # Act
        await image_usecase.upsert_user_profile_picture(mock_txn, mock_upload_file, user_id)

        # Assert
        # 1. Validation was called
        mock_guess.assert_called_once()
        
        # 2. DB was updated
        mock_txn.execute.assert_called_once()
        args, kwargs = mock_txn.execute.call_args
        assert "UPDATE users" in args[0]
        assert "SET profile_pic_url =" in args[0]
        assert "WHERE id =" in args[0]
        assert "fakeuuid.jpg" in args[1][0]
        assert args[1][1] == user_id
        
        # 3. File was saved
        mock_makedirs.assert_called_with("images", exist_ok=True)
        mock_open.assert_called()
        mock_file_context.write.assert_called()
        
        # 4. Transaction committed
        mock_txn.commit.assert_called_once()
        mock_txn.rollback.assert_not_called()

    @patch("core.services.image_usecase.filetype.guess")
    async def test_upsert_user_profile_picture_file_too_large(
        self, mock_guess, image_usecase, mock_upload_file, mock_txn
    ):
        # Arrange
        # Seek to end to simulate large file
        mock_upload_file.file.seek(0, os.SEEK_END)
        mock_upload_file.file.write(b"0" * (MAX_FILE_SIZE + 1))
        
        # Act & Assert
        with pytest.raises(Exception, match="File too large"):
            await image_usecase.upsert_user_profile_picture(mock_txn, mock_upload_file, 1)
            
        mock_txn.rollback.assert_called_once()
        mock_txn.commit.assert_not_called()

    @patch("core.services.image_usecase.filetype.guess")
    async def test_upsert_user_profile_picture_invalid_file_type(
        self, mock_guess, image_usecase, mock_upload_file, mock_txn
    ):
        # Arrange
        mock_kind = MagicMock()
        mock_kind.mime = "application/pdf" # Not allowed
        mock_guess.return_value = mock_kind
        
        # Act & Assert
        with pytest.raises(Exception, match="Unsupported file type"):
            await image_usecase.upsert_user_profile_picture(mock_txn, mock_upload_file, 1)
            
        mock_txn.rollback.assert_called_once()
        mock_txn.commit.assert_not_called()

    @patch("core.services.image_usecase.filetype.guess")
    async def test_upsert_user_profile_picture_db_error_triggers_rollback(
        self, mock_guess, image_usecase, mock_upload_file, mock_txn
    ):
        # Arrange
        mock_kind = MagicMock()
        mock_kind.mime = "image/png"
        mock_kind.extension = "png"
        mock_guess.return_value = mock_kind
        
        mock_txn.execute.side_effect = Exception("DB Connection Lost")
        
        # Act & Assert
        with pytest.raises(Exception, match="Error in service layer while upserting image"):
            await image_usecase.upsert_user_profile_picture(mock_txn, mock_upload_file, 1)
            
        mock_txn.rollback.assert_called_once()
        mock_txn.commit.assert_not_called()

    @patch("core.services.image_usecase.filetype.guess")
    @patch("core.services.image_usecase.aiofiles.open")
    async def test_upsert_user_profile_picture_save_error_triggers_rollback(
        self, mock_open, mock_guess, image_usecase, mock_upload_file, mock_txn
    ):
        # Arrange
        mock_kind = MagicMock()
        mock_kind.mime = "image/webp"
        mock_kind.extension = "webp"
        mock_guess.return_value = mock_kind
        
        mock_open.side_effect = PermissionError("Permission denied")
        
        # Act & Assert
        with pytest.raises(Exception, match="Error in service layer while upserting image"):
            await image_usecase.upsert_user_profile_picture(mock_txn, mock_upload_file, 1)
            
        mock_txn.rollback.assert_called_once()
        mock_txn.commit.assert_not_called()
