from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator
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
    type: str = Field(
        ...,
        description="The type of the application (all, internal, external, restricted)",
    )
    description: Optional[str] = Field(
        None, description="A brief description of the application"
    )
    permissions: Optional[List[str]] = Field(
        None,
        description="List of available permissions for this application. Example: ['read', 'write']",
    )
    is_active: bool = Field(
        True, description="Indicates whether the application is active"
    )


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
        ...,
        description="The permissions of the user in the application. Example: {'read': 'read', 'write': 'write'}",
    )

    @field_validator("permissions", mode="before")
    @classmethod
    def convert_list_to_dict(cls, v):
        if isinstance(v, list):
            return {p: p for p in v}
        return v


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


class BulkLinkModel(BaseModel):
    permissions: List[str] = Field(default_factory=list)
    search: Optional[str] = ""


class UserApplicationDetailModel(BaseModel):
    application_id: int
    name: str
    uri: str
    type: str
    description: Optional[str] = None
    permissions: Dict[str, str] = Field(
        ..., description="The permissions of the user in this application."
    )
    app_permissions: List[str] = Field(
        default_factory=list,
        description="The list of all permissions defined for this application.",
    )
    is_active: bool
