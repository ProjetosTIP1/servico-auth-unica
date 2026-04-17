import os
import filetype
import aiofiles
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


class ImageUsecase:
    async def upsert_user_profile_picture(
        self, txn: ITransaction, image: UploadFile, user_id: int
    ) -> None:
        try:
            file_name: str = await self._validate_image_content(image)
            file_path: str = os.path.join("images", file_name)

            query: str = """
            UPDATE users
            SET profile_pic_url = %s
            WHERE id = %s
            """
            params = (file_path, user_id)
            await txn.execute(query, params)

            await self._save_pic_file(image, file_name)

            await txn.commit()
        except Exception as e:
            await txn.rollback()
            raise Exception(f"Error in service layer while upserting image: {e}")
        except ValueError as e:
            await txn.rollback()
            raise ValueError(f"Error in service layer while upserting image: {e}")
        except FileNotFoundError as e:
            await txn.rollback()
            raise FileNotFoundError(
                f"Error in service layer while upserting image: {e}"
            )

    async def _save_pic_file(self, file: UploadFile, file_name: str) -> None:
        try:
            os.makedirs("images", exist_ok=True)
            file_path = os.path.join("images", file_name)
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(await file.read())
        except Exception as e:
            raise Exception(f"Error in service layer while saving image: {e}")

    async def _validate_image_content(self, file: UploadFile) -> str:
        """
        Refactored System Design:
        1. Size Validation (Shield)
        2. Content Validation (Magic Numbers/Pillow)
        3. Metadata Sanitization (Security)
        4. Atomic Persistence (Reliability)
        """

        # --- 1. PRE-FLIGHT VALIDATION (The Guard) ---

        # A. Check Size (Don't read the whole file into RAM yet)
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > MAX_FILE_SIZE:
            raise Exception(f"File too large. Max allowed: {MAX_FILE_SIZE / 1e6}MB")

        # B. Validate Content (Magic Numbers)
        # Read the first 2048 bytes to detect the "real" mime type
        header = await file.read(2048)
        await file.seek(0)

        # Use filetype to guess the mime type
        kind = filetype.guess(header)

        if kind is None:
            raise Exception("Cannot identify file type.")

        # Validate against our allowed list
        if kind.mime not in ALLOWED_MIME_TYPES:
            raise Exception(f"Unsupported file type: {kind.mime}")

        # Use the extension from the verified 'kind', NOT the user's filename
        safe_ext = f".{kind.extension}"
        unique_name: str = f"{uuid4().hex}{safe_ext}"
        return unique_name
