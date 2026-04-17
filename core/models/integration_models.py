from pydantic import BaseModel, Field
from typing import Optional


class IntegrationUnit(BaseModel):
    id: int = Field(description="Internal ID of the unit in SAM")
    sigla: str = Field(description="Abbreviation/Code of the unit")


class IntegrationDepartment(BaseModel):
    id: str = Field(description="Unique code/ID of the department")
    name: str = Field(description="Name of the department")


class IntegrationPosition(BaseModel):
    code: str = Field(description="Unique code of the position/cargo")
    name: str = Field(description="Name of the position")
    branch: Optional[str] = Field(
        default=None, description="Branch/Filial associated with the position"
    )


class IntegrationUser(BaseModel):
    username: str = Field(description="Unique username (cleaned CNPJ/CPF)")
    full_name: str = Field(description="Full name of the user")
    email: Optional[str] = Field(default=None, description="Email address")
    unit_id: Optional[int] = Field(default=None, description="Mapped Unit ID")
    position_id: Optional[int] = Field(default=None, description="Mapped Position ID")
    department_id: Optional[str] = Field(
        default=None, description="Mapped Department ID"
    )
    is_active: bool = Field(default=True, description="Active status")
    is_integrated: bool = Field(
        default=True, description="Indicates if the user was integrated from SGA"
    )


# ── DTOs for Source Data (SGA) ─────────────────────────────────────────────


class SgaUserDTO(BaseModel):
    """Data Transfer Object for users fetched from SGA (SQL Server)"""

    username: str
    nome_completo: str
    registration_number: str
    email: Optional[str] = None
    unidade_sigla: str = Field(alias="UNIDADE")
    cargo_codigo: str = Field(alias="cargo")
    departamento_codigo: str = Field(alias="Departamento")
    is_active: Optional[bool] = True


class SgaDepartmentDTO(BaseModel):
    """Data Transfer Object for departments fetched from SGA"""

    codigo: str = Field(alias="Codigo")
    nome: str = Field(alias="Nome")


class SgaPositionDTO(BaseModel):
    """Data Transfer Object for positions/cargos fetched from SGA"""

    codigo: str = Field(alias="Codigo")
    nome: str = Field(alias="Nome")
    departamento: str = Field(alias="Departamento")
    filial: str = Field(alias="Filial")
