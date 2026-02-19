from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class CredentialModel(BaseModel):
    username: str = Field(default=..., description="The username of the user")
    password: str = Field(default=..., description="The password of the user")

class AccessTokenType(BaseModel):
    token: str = Field(default=..., description="The access token string")
    expires_in: int = Field(default=..., description="Time in seconds until the token expires")
    token_type: str = Field(default="Bearer", description="The type of the token, e.g., 'Bearer'")
    refresh_token: str = Field(default=..., description="The refresh token string")
    user_id: int = Field(default=..., description="The ID of the user associated with the token")
    application_id: int = Field(default=..., description="The ID of the application that issued the token")
    issued_at: datetime = Field(default=..., description="The time when the token was issued")

class RefreshTokenType(BaseModel):
    token: str = Field(default=..., description="The refresh token string")
    expires_in: int = Field(default=..., description="Time in seconds until the refresh token expires")
    token_type: str = Field(default="Refresh", description="The type of the token, e.g., 'Refresh'")
    user_id: int = Field(default=..., description="The ID of the user associated with the refresh token")
    application_id: int = Field(default=..., description="The ID of the application that issued the refresh token")
    issued_at: datetime = Field(default=..., description="The time when the refresh token was issued")
    revoked: bool = Field(default=False, description="Indicates whether the refresh token has been revoked")
    consumed_at: Optional[datetime] = Field(default=None, description="The time when the refresh token was consumed. Set when the token is used to obtain a new access token. Is None if the token has not been used yet.")
