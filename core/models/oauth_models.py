from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class ResponseModel(BaseModel):
    code: int = Field(default=..., description="The HTTP status code of the response")
    status: str = Field(
        default=...,
        description="The status of the response, typically 'success' or 'error'",
    )
    message: str = Field(default=..., description="A message describing the response")
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="The data returned in the response, if any"
    )


class TokenModel(BaseModel):
    id: int = Field(default=..., description="The unique identifier of the token")
    user_id: int = Field(
        default=..., description="The ID of the user associated with the token"
    )
    token: str = Field(default=..., description="The token string, typically a JWT")
    type: TokenType = Field(
        default=..., description="The type of the token, either 'access' or 'refresh'"
    )
    parent_token: str = Field(
        default=...,
        description="The parent token string, if this token is an access token",
    )
    revoked: bool = Field(
        default=False, description="Indicates whether the token has been revoked"
    )
    consumed_at: Optional[datetime] = Field(
        default=None,
        description="The timestamp when the token was consumed, if applicable",
    )
    expires_at: datetime = Field(
        default=..., description="The timestamp when the token expires"
    )
    created_at: datetime = Field(
        default=..., description="The timestamp when the token was created"
    )
    updated_at: datetime = Field(
        default=..., description="The timestamp when the token was last updated"
    )


class TokenCreateModel(BaseModel):
    user_id: int = Field(
        default=..., description="The ID of the user associated with the token"
    )
    token: str = Field(default=..., description="The token string, typically a JWT")
    type: TokenType = Field(
        default=..., description="The type of the token, either 'access' or 'refresh'"
    )
    parent_token: str = Field(
        default=...,
        description="The parent token string, if this token is an access token",
    )
    expires_at: datetime = Field(
        default=..., description="The timestamp when the token expires"
    )


class TokenUpdateModel(BaseModel):
    token: str = Field(
        default=..., description="The token string to identify the token to update"
    )
    revoked: Optional[bool] = Field(
        default=None, description="Indicates whether the token has been revoked"
    )
    consumed_at: Optional[datetime] = Field(
        default=None,
        description="The timestamp when the token was consumed, if applicable",
    )
    expires_at: Optional[datetime] = Field(
        default=None, description="The timestamp when the token expires"
    )


class TokenResponseModel(BaseModel):
    access_token: str = Field(
        default=..., description="The access token string, typically a JWT"
    )
    refresh_token: str = Field(
        default=..., description="The refresh token string, typically a JWT"
    )
    expires_in: datetime = Field(
        default=..., description="The timestamp when the token expires"
    )


class TokenRequestModel(BaseModel):
    user_id: int = Field(
        default=..., description="The ID of the user associated with the token"
    )
    access_token: Optional[str] = Field(
        default=None, description="The access token string, typically a JWT"
    )
    refresh_token: Optional[str] = Field(
        default=None, description="The refresh token string, typically a JWT"
    )


class CredentialModel(BaseModel):
    username: str = Field(default=..., description="The username of the user")
    password: str = Field(default=..., description="The password of the user")
