from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ApplicationModel(BaseModel):
    client_id: str = Field(default=..., description="The client ID of the application") 
    client_secret: str = Field(default=..., description="The client secret of the application")
    skip_authorization: bool = Field(default=False, description="Indicates whether the application should skip the authorization step during the OAuth flow")
    authorization_grant_type: str = Field(default=..., description="The authorization grant type used by the application, e.g., 'authorization_code', 'client_credentials', etc.")
    name: str = Field(default=..., description="The name of the system URI")
    is_active: bool = Field(default=True, description="Indicates whether the system URI is active")
    url: str = Field(default=..., description="The URL of the system")
    created_at: datetime = Field(default=..., description="The creation date of the system URI in ISO format")
    updated_at: Optional[datetime] = Field(default=None, description="The last update date of the system URI in ISO format")

class ApplicationCreateModel(BaseModel):
    client_id: str = Field(default=..., description="The client ID of the application") 
    client_secret: str = Field(default=..., description="The client secret of the application")
    skip_authorization: bool = Field(default=False, description="Indicates whether the application should skip the authorization step during the OAuth flow")
    authorization_grant_type: str = Field(default=..., description="The authorization grant type used by the application, e.g., 'authorization_code', 'client_credentials', etc.")
    name: str = Field(default=..., description="The name of the system URI")
    url: str = Field(default=..., description="The URL of the system")

class ApplicationUpdateModel(BaseModel):
    client_secret: Optional[str] = Field(default=None, description="The client secret of the application")
    skip_authorization: Optional[bool] = Field(default=None, description="Indicates whether the application should skip the authorization step during the OAuth flow")
    authorization_grant_type: Optional[str] = Field(default=None, description="The authorization grant type used by the application, e.g., 'authorization_code', 'client_credentials', etc.")
    is_active: Optional[bool] = Field(default=None, description="Indicates whether the system URI is active")
    name: Optional[str] = Field(default=None, description="The name of the system URI")
    url: Optional[str] = Field(default=None, description="The URL of the system")