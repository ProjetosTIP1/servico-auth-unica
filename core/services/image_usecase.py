import os
import filetype
import aiofiles
from io import BytesIO
from typing import Protocol, runtime_checkable
from uuid import uuid4
from fastapi import UploadFile

from core.ports.infrastructure import ITransaction

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif"}
# Maps mime types to safe extensions to avoid trusting user-provided extensions
MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/avif": ".avif",
}


@runtime_checkable
class FileLike(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...
    def seek(self, offset: int, whence: int = 0, /) -> int: ...
    def tell(self, /) -> int: ...


class ImageUsecase:
    async def upsert_user_profile_picture(
        self, txn: ITransaction, image: UploadFile, user_id: int
    ) -> None:
        """Endpoint-facing method using FastAPI's UploadFile."""
        try:
            # We don't read the whole file into memory yet
            await self._execute_upsert(txn, image.file, user_id)
            await txn.commit()
        except Exception as e:
            await txn.rollback()
            raise Exception(f"Error in service layer while upserting image: {e}")

    async def upsert_from_bytes(
        self, txn: ITransaction, content: bytes, user_id: int
    ) -> None:
        """Service-to-service method using raw bytes (e.g. from MS Graph)."""
        try:
            file_obj = BytesIO(content)
            await self._execute_upsert(txn, file_obj, user_id)
            await txn.commit()
        except Exception as e:
            await txn.rollback()
            raise Exception(
                f"Error in service layer while upserting image from bytes: {e}"
            )

    async def _execute_upsert(
        self, txn: ITransaction, file: FileLike, user_id: int
    ) -> None:
        """Core logic separated from data source."""
        file_name = await self._validate_image_content(file)
        file_path = os.path.join("images", file_name)

        query = """
        UPDATE users
        SET profile_picture_url = :file_path
        WHERE id = :id
        """
        await txn.execute(query, {"file_path": file_path, "id": user_id})
        await self._save_pic_file(file, file_name)

    async def _save_pic_file(self, file: FileLike, file_name: str) -> None:
        try:
            os.makedirs("images", exist_ok=True)
            file_path = os.path.join("images", file_name)

            # Ensure we are at the start of the file
            if hasattr(file, "seek"):
                file.seek(0)

            content = file.read()
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)
        except Exception as e:
            raise Exception(f"Error in service layer while saving image: {e}")

    async def _validate_image_content(self, file: FileLike) -> str:
        # A. Check Size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Max allowed: {MAX_FILE_SIZE / 1e6}MB")

        # B. Validate Content (Magic Numbers)
        header = file.read(2048)
        file.seek(0)

        kind = filetype.guess(header)
        if kind is None:
            raise ValueError("Cannot identify file type.")

        if kind.mime not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Unsupported file type: {kind.mime}")

        safe_ext = f".{kind.extension}"
        return f"{uuid4().hex}{safe_ext}"
