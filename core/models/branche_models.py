from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class BranchModel(BaseModel):
    id: int = Field(default=..., description="The unique identifier of the branch")
    name: str = Field(default=..., description="The name of the branch")
    city: str = Field(default=..., description="The city of the branch")
    acronym: str = Field(default=..., description="The acronym of the branch")
    manager_name: Optional[str] = Field(
        default=None, description="The name of the branch manager"
    )
    description: Optional[str] = Field(
        default=None, description="A brief description of the branch"
    )
    created_at: datetime = Field(
        default=..., description="The creation date of the branch in ISO format"
    )
    updated_at: Optional[datetime] = Field(
        default=None, description="The last update date of the branch in ISO format"
    )


class BranchCreateModel(BaseModel):
    name: str = Field(default=..., description="The name of the branch")
    city: str = Field(default=..., description="The city of the branch")
    acronym: str = Field(default=..., description="The acronym of the branch")
    manager_id: Optional[str] = Field(
        default=None, description="The ID of the branch manager"
    )
    description: Optional[str] = Field(
        default=None, description="A brief description of the branch"
    )


class BranchUpdateModel(BaseModel):
    name: Optional[str] = Field(default=None, description="The name of the branch")
    city: Optional[str] = Field(default=None, description="The city of the branch")
    acronym: Optional[str] = Field(
        default=None, description="The acronym of the branch"
    )
    manager_id: Optional[str] = Field(
        default=None, description="The ID of the branch manager"
    )
    description: Optional[str] = Field(
        default=None, description="A brief description of the branch"
    )
