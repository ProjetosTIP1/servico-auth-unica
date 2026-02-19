from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class UnitType(BaseModel):
    id: int = Field(default=..., description="The unique identifier of the unit")
    name: str = Field(default=..., description="The name of the unit")
    description: Optional[str] = Field(
        default=None, description="A brief description of the unit"
    )
    is_active: bool = Field(
        default=True, description="Indicates whether the unit is active"
    )
    created_at: datetime = Field(
        default=..., description="The time when the unit was created"
    )
    updated_at: datetime = Field(
        default=..., description="The time when the unit was last updated"
    )


class UnitCreateType(BaseModel):
    name: str = Field(default=..., description="The name of the unit")
    description: Optional[str] = Field(
        default=None, description="A brief description of the unit"
    )


class UnitUpdateType(BaseModel):
    name: Optional[str] = Field(default=None, description="The name of the unit")
    description: Optional[str] = Field(
        default=None, description="A brief description of the unit"
    )
    is_active: Optional[bool] = Field(
        default=None, description="Indicates whether the unit is active"
    )
