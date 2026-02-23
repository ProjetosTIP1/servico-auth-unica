from typing import List
from core.ports.repository import IUserRepository
from core.ports.infrastructure import IDatabase

from core.models.user_models import UserType, UserUpdateType, UserCreateType


class UserRepository(IUserRepository):
    def __init__(self, db: IDatabase):
        self.db = db

    async def get_user_by_username(self, username: str) -> UserType:
        """Get user by username"""
        try:
            query = """
            SELECT id, username, email, full_name, first_name, last_name, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
            FROM users 
            WHERE username = :username AND is_active = 1
            """
            results = await self.db.execute_with_params(query, {"username": username})
            if results:
                user_data = results[0]
                return UserType(**user_data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching user by username: {e}")

    async def get_user_by_id(self, user_id: int) -> UserType:
        """Get user by ID"""
        try:
            query = """
            SELECT id, username, email, full_name, first_name, last_name, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
            FROM users 
            WHERE id = :id AND is_active = 1
            """
            results = await self.db.execute_with_params(query, {"id": user_id})
            if results:
                user_data = results[0]
                return UserType(**user_data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching user by ID: {e}")

    async def get_user_hashed_password(self, username: str) -> str:
        """Get the hashed password for a user by username"""
        try:
            query = """
            SELECT hashed_password 
            FROM users 
            WHERE username = :username AND is_active = 1
            """
            results = await self.db.execute_with_params(query, {"username": username})
            if results:
                return results[0]["hashed_password"]
            return None
        except Exception as e:
            raise Exception(f"Error fetching hashed password: {e}")

    async def create_user(
        self, user_data: UserCreateType, hashed_password: str
    ) -> UserType:
        """Create a new user"""
        try:
            query = """
            INSERT INTO users (username, email, full_name, first_name, last_name, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, hashed_password) 
            VALUES (:username, :email, :full_name, :first_name, :last_name, :unit, :job, :branche, :cpf_cnpj, :registration_number, :profile_picture_url, :hashed_password)
            """
            await self.db.execute_with_params(
                query, {**user_data.dict(), "hashed_password": hashed_password}
            )
            return await self.get_user_by_username(user_data.username)
        except Exception as e:
            raise Exception(f"Error creating user: {e}")

    async def list_users(self) -> List[UserType]:
        """List all users"""
        try:
            query = """
            SELECT id, username, email, full_name, first_name, last_name, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, is_active, created_at, updated_at 
            FROM users 
            WHERE is_active = 1
            """
            results = await self.db.execute(query)
            return [UserType(**data) for data in results]
        except Exception as e:
            raise Exception(f"Error listing users: {e}")

    async def update_user(self, user_id: int, user_data: UserUpdateType) -> UserType:
        """Update an existing user"""
        try:
            query = """
            UPDATE users 
            SET username = :username, email = :email, full_name = :full_name, first_name = :first_name, last_name = :last_name, unit = :unit, job = :job, branche = :branche, cpf_cnpj = :cpf_cnpj, registration_number = :registration_number, profile_picture_url = :profile_picture_url 
            WHERE id = :id
            """
            await self.db.execute_with_params(
                query,
                {
                    "username": user_data.username,
                    "email": user_data.email,
                    "full_name": user_data.full_name,
                    "id": user_id,
                },
            )
            return await self.get_user_by_username(user_data.username)
        except Exception as e:
            raise Exception(f"Error updating user: {e}")

    async def update_user_password(self, user_id: int, hashed_password: str) -> None:
        """Update the password of an existing user"""
        try:
            query = """
            UPDATE users 
            SET hashed_password = :hashed_password 
            WHERE id = :id
            """
            await self.db.execute_with_params(
                query, {"hashed_password": hashed_password, "id": user_id}
            )
        except Exception as e:
            raise Exception(f"Error updating user password: {e}")

    async def delete_user(self, user_id: int) -> None:
        """Soft delete a user by ID"""
        try:
            query = """
            UPDATE users 
            SET is_active = 0 
            WHERE id = :id
            """
            await self.db.execute_with_params(query, {"id": user_id})
        except Exception as e:
            raise Exception(f"Error deleting user: {e}")
