from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class JobType(BaseModel):
    id: int = Field(default=..., description="The unique identifier of the job")
    erp_id: Optional[str] = Field(
        default=None, description="The identifier of the job in the ERP system"
    )
    name: str = Field(default=..., description="The name of the job")
    description: Optional[str] = Field(
        default=None, description="A brief description of the job"
    )
    unit: Optional[str] = Field(
        default=None, description="The unit or department the job belongs to"
    )
    sector: Optional[str] = Field(
        default=None, description="The sector or area of expertise of the job"
    )
    is_active: bool = Field(
        default=True, description="Indicates whether the job is active"
    )
    created_at: datetime = Field(
        default=..., description="The time when the job was created"
    )
    updated_at: datetime = Field(
        default=..., description="The time when the job was last updated"
    )


class JobCreateType(BaseModel):
    erp_id: Optional[str] = Field(
        default=None, description="The identifier of the job in the ERP system"
    )
    name: str = Field(default=..., description="The name of the job")
    description: Optional[str] = Field(
        default=None, description="A brief description of the job"
    )
    unit_id: Optional[int] = Field(
        default=None, description="The unit or department the job belongs to"
    )
    sector_id: Optional[int] = Field(
        default=None, description="The sector or area of expertise of the job"
    )


class JobUpdateType(BaseModel):
    erp_id: Optional[str] = Field(
        default=None, description="The identifier of the job in the ERP system"
    )
    name: Optional[str] = Field(default=None, description="The name of the job")
    description: Optional[str] = Field(
        default=None, description="A brief description of the job"
    )
    unit_id: Optional[int] = Field(
        default=None, description="The unit or department the job belongs to"
    )
    sector_id: Optional[int] = Field(
        default=None, description="The sector or area of expertise of the job"
    )
    is_active: Optional[bool] = Field(
        default=None, description="Indicates whether the job is active"
    )
