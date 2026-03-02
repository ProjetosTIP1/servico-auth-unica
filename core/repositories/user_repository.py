from typing import List
from core.ports.repository import IUserRepository
from core.ports.infrastructure import IDatabase

from core.models.user_models import UserType, UserUpdateType, UserCreateType

from core.helpers.sql_helper import filter_valid_update_clauses


class UserRepository(IUserRepository):
    def __init__(self, db: IDatabase):
        self.db = db

    async def get_user_by_username(self, username: str) -> UserType | None:
        """Get user by username"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
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

    async def get_user_by_id(self, user_id: int) -> UserType | None:
        """Get user by ID"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
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

    async def get_user_by_email(self, email: str) -> UserType | None:
        """Get user by email"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
            FROM users 
            WHERE email = :email AND is_active = 1
            """
            results = await self.db.execute_with_params(query, {"email": email})
            if results:
                user_data = results[0]
                return UserType(**user_data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching user by email: {e}")

    async def get_user_by_ms_oid(self, ms_oid: str) -> UserType | None:
        """Get user by Microsoft object ID"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
            FROM users 
            WHERE ms_oid = :ms_oid AND is_active = 1
            """
            results = await self.db.execute_with_params(query, {"ms_oid": ms_oid})
            if results:
                user_data = results[0]
                return UserType(**user_data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching user by MS OID: {e}")

    async def get_user_hashed_password(self, username: str) -> str | None:
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
            INSERT INTO users (username, email, ms_oid, full_name, first_name, last_name, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, hashed_password) 
            VALUES (:username, :email, :ms_oid, :full_name, :first_name, :last_name, :unit, :job, :branche, :cpf_cnpj, :registration_number, :profile_picture_url, :hashed_password)
            """
            await self.db.execute_with_params(
                query, {**user_data.model_dump(), "hashed_password": hashed_password}
            )
            new_user: UserType | None = await self.get_user_by_username(user_data.username)
            if new_user is None:
                raise Exception("Error creating user: User not found after creation")
            return new_user
        except Exception as e:
            raise Exception(f"Error creating user: {e}")

    async def list_users(self) -> List[UserType]:
        """List all users"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, is_active, created_at, updated_at 
            FROM users 
            WHERE is_active = 1
            """
            results = await self.db.execute(query)
            return [UserType(**data) for data in results]
        except Exception as e:
            raise Exception(f"Error listing users: {e}")

    async def update_user(self, user_id: int, user_data: UserUpdateType) -> UserType:
        """Partially update a user — only columns that were explicitly set are touched."""
        try:
            # Build the SET clause only from the fields the client actually sent.
            # model_dump(exclude_unset=True) ignores fields that were never provided,
            # even if they allow None (i.e. optional fields keep their DB value).
            fields = user_data.model_dump(exclude_unset=True)
            if not fields:
                user: UserType | None = await self.get_user_by_id(user_id)
                if user is None:
                    raise Exception("User not found")
                return user

            set_clause, params = filter_valid_update_clauses(fields, user_id)

            query = f"""
            UPDATE users
            SET {set_clause}, updated_at = NOW()
            WHERE id = :id
            """
            await self.db.execute_with_params(query, params)
            up_user: UserType | None = await self.get_user_by_id(user_id)
            if up_user is None:
                raise Exception("User not found after update")
            return up_user
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
