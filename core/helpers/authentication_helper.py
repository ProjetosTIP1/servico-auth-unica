from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

from core.config.settings import settings
from core.helpers.logger_helper import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/o/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    Passwords are encoded to UTF-8 before verification (required by bcrypt).
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """
    Hash a plain password using bcrypt.
    Returns a string (bcrypt returns bytes, decoded to str for storage).
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def validate_token(token: str) -> Optional[dict]:
    """
    Validate a JWT token and return its payload if valid.
    Returns None if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        if username is None:
            return None
        return payload
    except JWTError:
        return None


def create_jwt_token(
    data: dict, expires_delta: timedelta | None = None, token_type: str = "access"
) -> str:
    """Create a JWT access or refresh token"""
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire, "type": token_type})
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(
            message=f"Error creating JWT token: {e}",
            error_path="AuthenticationHelper.create_jwt_token",
        )
        raise Exception(f"Error creating JWT token: {e}")
