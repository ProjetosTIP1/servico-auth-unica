from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class UserType(BaseModel):
    id: int = Field(default=..., description="The unique identifier of the user")
    username: str = Field(default=..., description="The username of the user")
    email: str = Field(default=..., description="The email address of the user")
    is_active: bool = Field(
        default=True, description="Indicates whether the user account is active"
    )
    manager: Optional[bool] = Field(
        default=False, description="The name of the user's manager or supervisor"
    )
    full_name: Optional[str] = Field(
        default=None, description="The full name of the user"
    )
    first_name: Optional[str] = Field(
        default=None, description="The first name of the user"
    )
    last_name: Optional[str] = Field(
        default=None, description="The last name of the user"
    )
    unit: Optional[str] = Field(
        default=None, description="The unit or department the user belongs to"
    )
    job: Optional[str] = Field(
        default=None, description="The job title or position of the user"
    )
    branche: Optional[str] = Field(
        default=None, description="The branch or division of the user"
    )
    cpf_cnpj: Optional[str] = Field(
        default=None, description="The CPF or CNPJ number of the user"
    )
    registration_number: Optional[str] = Field(
        default=None, description="The registration number or employee ID of the user"
    )
    profile_picture_url: Optional[str] = Field(
        default=None, description="The URL of the user's profile picture"
    )
    created_at: datetime = Field(
        default=..., description="The time when the user account was created"
    )
    updated_at: datetime = Field(
        default=..., description="The time when the user account was last updated"
    )


class UserCreateType(BaseModel):
    username: str = Field(default=..., description="The username of the user")
    email: str = Field(default=..., description="The email address of the user")
    password: str = Field(default=..., description="The password for the user account")
    full_name: Optional[str] = Field(
        default=None, description="The full name of the user"
    )
    first_name: Optional[str] = Field(
        default=None, description="The first name of the user"
    )
    last_name: Optional[str] = Field(
        default=None, description="The last name of the user"
    )
    unit: Optional[str] = Field(
        default=None, description="The unit or department the user belongs to"
    )
    job: Optional[str] = Field(
        default=None, description="The job title or position of the user"
    )
    branche: Optional[str] = Field(
        default=None, description="The branch or division of the user"
    )
    cpf_cnpj: Optional[str] = Field(
        default=None, description="The CPF or CNPJ number of the user"
    )
    registration_number: Optional[str] = Field(
        default=None, description="The registration number or employee ID of the user"
    )
    profile_picture_url: Optional[str] = Field(
        default=None, description="The URL of the user's profile picture"
    )


class UserUpdateType(BaseModel):
    email: Optional[str] = Field(
        default=None, description="The email address of the user"
    )
    full_name: Optional[str] = Field(
        default=None, description="The full name of the user"
    )
    first_name: Optional[str] = Field(
        default=None, description="The first name of the user"
    )
    last_name: Optional[str] = Field(
        default=None, description="The last name of the user"
    )
    unit: Optional[str] = Field(
        default=None, description="The unit or department the user belongs to"
    )
    job: Optional[str] = Field(
        default=None, description="The job title or position of the user"
    )
    branche: Optional[str] = Field(
        default=None, description="The branch or division of the user"
    )
    cpf_cnpj: Optional[str] = Field(
        default=None, description="The CPF or CNPJ number of the user"
    )
    registration_number: Optional[str] = Field(
        default=None, description="The registration number or employee ID of the user"
    )
    profile_picture_url: Optional[str] = Field(
        default=None, description="The URL of the user's profile picture"
    )


class UserInDBType(UserType):
    hashed_password: str = Field(
        default=..., description="The hashed password of the user account"
    )


class UserUpdatePasswordType(BaseModel):
    user_id: int = Field(default=..., description="The unique identifier of the user")
    current_password: str = Field(
        default=..., description="The current password of the user"
    )
    new_password: str = Field(
        default=..., description="The new password for the user account"
    )


# ── Microsoft / Azure AD identity ─────────────────────────────────────────────


class MicrosoftUserIdentity(BaseModel):
    """
    Value object produced after a Microsoft JWT is successfully validated.

    This is a pure Domain model — it has zero dependency on MSAL or any
    infrastructure detail. The adapter maps the raw JWT claims to this type
    so that the rest of the application never touches raw token dicts.
    """

    oid: str = Field(
        description="Immutable Azure AD object ID — use this as the stable user key."
    )
    email: str = Field(
        description="User's primary email address (UPN or 'email' claim)."
    )
    name: Optional[str] = Field(default=None, description="Display name.")
    given_name: Optional[str] = Field(default=None, description="First name.")
    family_name: Optional[str] = Field(default=None, description="Last name.")
    tenant_id: Optional[str] = Field(
        default=None, description="Azure AD tenant ID (tid claim)."
    )
    preferred_username: Optional[str] = Field(
        default=None, description="Preferred login username."
    )
    roles: list[str] = Field(
        default_factory=list,
        description="App roles assigned to the user in Azure AD (roles claim).",
    )
