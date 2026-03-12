from typing import List
from abc import ABC, abstractmethod

from core.models.oauth_models import TokenModel, TokenCreateModel, TokenUpdateModel
from core.models.user_models import UserType, UserCreateType, UserUpdateType


class ITokenRepository(ABC):
    @abstractmethod
    async def create_access_token(self, token: TokenCreateModel) -> TokenModel:
        """Create a new access token for the given user information."""
        pass

    @abstractmethod
    async def create_refresh_token(self, token: TokenCreateModel) -> TokenModel:
        """Create a new refresh token for the given user information."""
        pass

    @abstractmethod
    async def get_last_refresh_token(self, user_id: str) -> TokenModel:
        """Retrieve the last refresh token for the given user ID."""
        pass

    @abstractmethod
    async def get_token_by_string(self, token: str) -> TokenModel | None:
        """Retrieve a token by its string value."""
        pass

    @abstractmethod
    async def update(self, token: TokenUpdateModel) -> TokenModel:
        """Update the given token and return the updated token."""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> None:
        """Revoke the given token."""
        pass

    @abstractmethod
    async def revoke_all_user_tokens(self, user_id: int) -> None:
        """Revoke all tokens for the given user ID."""
        pass


class IUserRepository(ABC):
    """Abstract interface for user repository operations"""

    @abstractmethod
    async def get_user_by_cpfcnpj(self, cpfcnpj: str) -> UserType | None:
        """Get user by CPF/CNPJ"""
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> UserType | None:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> UserType | None:
        """Get user by email"""
        pass

    @abstractmethod
    async def get_user_by_ms_oid(self, ms_oid: str) -> UserType | None:
        """Get user by Microsoft object ID"""
        pass

    @abstractmethod
    async def search_users_by_name(self, name_query: str) -> List[UserType]:
        """Search users by name (partial match)"""
        pass

    @abstractmethod
    async def get_user_hashed_password(self, email: str) -> str | None:
        """Get the hashed password for a user by email"""
        pass

    @abstractmethod
    async def is_user_admin(self, cpf_cnpj: str) -> bool:
        """Check if the user with the given CPF/CNPJ is an admin"""
        pass

    @abstractmethod
    async def create_user(
        self, user_data: UserCreateType, hashed_password: str
    ) -> UserType:
        """Create a new user"""
        pass

    @abstractmethod
    async def list_users(self) -> List[UserType]:
        """List all users"""
        pass

    @abstractmethod
    async def update_user(self, user_id: int, user_data: UserUpdateType) -> UserType:
        """Update an existing user"""
        pass

    @abstractmethod
    async def update_user_password(
        self, user_id: int, hashed_password: str
    ) -> UserType | None:
        """Update the password of an existing user"""
        pass

    @abstractmethod
    async def delete_user(self, user_id: int) -> None:
        """Soft delete a user by ID"""
        pass


class ISgaRepository(ABC):
    """Interface for extracting data from SGA (SQL Server) using Polars"""

    @abstractmethod
    def get_users_df(self):
        """Fetch all active users from SGA as a Polars DataFrame"""
        pass

    @abstractmethod
    def get_disabled_users_df(self):
        """Fetch users to be disabled from SGA as a Polars DataFrame"""
        pass

    @abstractmethod
    def get_departments_df(self):
        """Fetch all departments from SGA as a Polars DataFrame"""
        pass

    @abstractmethod
    def get_positions_df(self):
        """Fetch all positions/cargos from SGA as a Polars DataFrame"""
        pass


class ISamIntegrationRepository(ABC):
    """Interface for synchronizing and fetching state from SAM (MariaDB)"""

    @abstractmethod
    def get_current_users_df(self):
        """Fetch current users from SAM as a Polars DataFrame for comparison"""
        pass

    @abstractmethod
    def get_units_mapping_df(self):
        """Fetch units mapping (Sigla -> ID) from SAM"""
        pass

    @abstractmethod
    def get_positions_mapping_df(self):
        """Fetch positions mapping (Codigo -> ID) from SAM"""
        pass

    @abstractmethod
    def upsert_departments(self, df) -> int:
        """Batch upsert departments into SAM"""
        pass

    @abstractmethod
    def upsert_positions(self, df) -> int:
        """Batch upsert positions into SAM"""
        pass

    @abstractmethod
    def upsert_users(self, df) -> int:
        """Batch upsert users into SAM (new and updates)"""
        pass

    @abstractmethod
    def disable_users(self, usernames: list[str]) -> int:
        """Batch disable users in SAM"""
        pass
