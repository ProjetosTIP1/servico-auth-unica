from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from enum import Enum


class PermissionEnum(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    DENIED = "denied"


class ApplicationType(str, Enum):
    ALL = "all"
    INTERNAL = "internal"
    EXTERNAL = "external"
    RESTRICTED = "restricted"


class ApplicationBase(BaseModel):
    name: str = Field(..., description="The name of the application")
    uri: str = Field(..., description="The URI of the application")
    type: str = Field(..., description="The type of the application (all, internal, external, restricted)")
    description: Optional[str] = Field(None, description="A brief description of the application")
    permissions: Optional[List[str]] = Field(
        None, description="List of available permissions for this application. Example: ['read', 'write']"
    )
    is_active: bool = Field(True, description="Indicates whether the application is active")


class ApplicationCreateModel(ApplicationBase):
    pass


class ApplicationUpdateModel(BaseModel):
    name: Optional[str] = None
    uri: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ApplicationModel(ApplicationBase):
    id: int
    created_at: datetime
    updated_at: datetime


class UserApplicationBase(BaseModel):
    user_id: int
    application_id: int
    permissions: Dict[str, str] = Field(
        ..., description="The permissions of the user in the application. Example: {'read': 'read', 'write': 'write'}"
    )


class UserApplicationCreateModel(UserApplicationBase):
    pass


class UserApplicationUpdateModel(BaseModel):
    permissions: Dict[str, str]


class UserApplicationModel(UserApplicationBase):
    id: int
    created_at: datetime
    updated_at: datetime


class UserWithPermissionsModel(BaseModel):
    user_id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    permissions: Dict[str, str]
