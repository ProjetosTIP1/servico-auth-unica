from typing import List
from core.ports.repository import IUserRepository
from core.ports.infrastructure import ITransaction

from core.models.user_models import UserType, UserUpdateType, UserCreateType

from core.helpers.sql_helper import filter_valid_update_clauses


class UserRepository(IUserRepository):
    async def get_user_by_cpfcnpj(
        self, txn: ITransaction, cpfcnpj: str
    ) -> UserType | None:
        """Get user by CPF/CNPJ"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
            FROM users 
            WHERE cpf_cnpj = :cpf_cnpj AND is_active = 1
            """
            results = await txn.execute(query, {"cpf_cnpj": cpfcnpj})
            if results:
                user_data = results[0]
                return UserType(**user_data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching user by CPF/CNPJ: {e}")

    async def get_user_by_id(self, txn: ITransaction, user_id: int) -> UserType | None:
        """Get user by ID"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
            FROM users 
            WHERE id = :id AND is_active = 1
            """
            results = await txn.execute(query, {"id": user_id})
            if results:
                user_data = results[0]
                return UserType(**user_data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching user by ID: {e}")

    async def get_user_by_email(self, txn: ITransaction, email: str) -> UserType | None:
        """Get user by email"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
            FROM users 
            WHERE email = :email AND is_active = 1
            """
            results = await txn.execute(query, {"email": email})
            if results:
                user_data = results[0]
                return UserType(**user_data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching user by email: {e}")

    async def get_user_by_ms_oid(
        self, txn: ITransaction, ms_oid: str
    ) -> UserType | None:
        """Get user by Microsoft object ID"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
            FROM users 
            WHERE ms_oid = :ms_oid AND is_active = 1
            """
            results = await txn.execute(query, {"ms_oid": ms_oid})
            if results:
                user_data = results[0]
                return UserType(**user_data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching user by MS OID: {e}")

    async def search_users_by_name(
        self, txn: ITransaction, name_query: str
    ) -> List[UserType]:
        """Search users by name (partial match)"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, created_at, updated_at 
            FROM users 
            WHERE (full_name LIKE :name_query OR first_name LIKE :name_query OR last_name LIKE :name_query) AND is_active = 1
            """
            results = await txn.execute(query, {"name_query": f"%{name_query}%"})
            return [UserType(**data) for data in results]
        except Exception as e:
            raise Exception(f"Error searching users by name: {e}")

    async def get_user_hashed_password(
        self, txn: ITransaction, cpfcnpj: str
    ) -> str | None:
        """Get the hashed password for a user by CPF/CNPJ"""
        try:
            query = """
            SELECT hashed_password 
            FROM users 
            WHERE cpf_cnpj = :cpf_cnpj AND is_active = 1
            """
            results = await txn.execute(query, {"cpf_cnpj": cpfcnpj})
            if results:
                return results[0]["hashed_password"]
            return None
        except Exception as e:
            raise Exception(f"Error fetching hashed password: {e}")

    async def is_user_admin(self, txn: ITransaction, cpf_cnpj: str) -> bool:
        """Check if the user with the given CPF/CNPJ is an admin"""
        try:
            query = """
            SELECT manager 
            FROM users 
            WHERE cpf_cnpj = :cpf_cnpj AND is_active = 1
            """
            results = await txn.execute(query, {"cpf_cnpj": cpf_cnpj})
            if results:
                return results[0]["manager"] == 1
            return False
        except Exception as e:
            raise Exception(f"Error checking if user is admin: {e}")

    async def create_user(
        self, txn: ITransaction, user_data: UserCreateType, hashed_password: str
    ) -> UserType:
        """Create a new user"""
        try:
            query = """
            INSERT INTO users (username, email, ms_oid, full_name, first_name, last_name, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, hashed_password) 
            VALUES (:username, :email, :ms_oid, :full_name, :first_name, :last_name, :unit, :job, :branche, :cpf_cnpj, :registration_number, :profile_picture_url, :hashed_password)
            """
            await txn.execute(
                query, {**user_data.model_dump(), "hashed_password": hashed_password}
            )

            # Use the same transaction to get the user back
            # We use get_user_by_cpfcnpj as it's unique
            new_user: UserType | None = await self.get_user_by_cpfcnpj(
                txn, user_data.cpf_cnpj
            )
            if new_user is None:
                raise Exception("Error creating user: User not found after creation")
            return new_user
        except Exception as e:
            raise Exception(f"Error creating user: {e}")

    async def list_users(self, txn: ITransaction) -> List[UserType]:
        """List all users"""
        try:
            query = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, is_active, created_at, updated_at 
            FROM users 
            WHERE is_active = 1
            """
            results = await txn.execute(query)
            return [UserType(**data) for data in results]
        except Exception as e:
            raise Exception(f"Error listing users: {e}")

    async def update_user(
        self, txn: ITransaction, user_id: int, user_data: UserUpdateType
    ) -> UserType:
        """Partially update a user — only columns that were explicitly set are touched."""
        try:
            fields = user_data.model_dump(exclude_unset=True)
            if not fields:
                user: UserType | None = await self.get_user_by_id(txn, user_id)
                if user is None:
                    raise Exception("User not found")
                return user

            set_clause, params = filter_valid_update_clauses(fields, user_id)

            query = f"""
            UPDATE users
            SET {set_clause}, updated_at = NOW()
            WHERE id = :id
            """
            await txn.execute(query, params)
            up_user: UserType | None = await self.get_user_by_id(txn, user_id)
            if up_user is None:
                raise Exception("User not found after update")
            return up_user
        except Exception as e:
            raise Exception(f"Error updating user: {e}")

    async def update_user_password(
        self, txn: ITransaction, user_id: int, hashed_password: str
    ) -> None:
        """Update the password of an existing user"""
        try:
            query = """
            UPDATE users 
            SET hashed_password = :hashed_password 
            WHERE id = :id
            """
            await txn.execute(
                query, {"hashed_password": hashed_password, "id": user_id}
            )
        except Exception as e:
            raise Exception(f"Error updating user password: {e}")

    async def delete_user(self, txn: ITransaction, user_id: int) -> None:
        """Soft delete a user by ID"""
        try:
            query = """
            UPDATE users 
            SET is_active = 0 
            WHERE id = :id
            """
            await txn.execute(query, {"id": user_id})
        except Exception as e:
            raise Exception(f"Error deleting user: {e}")

    async def count_active_users(self, txn: ITransaction) -> int:
        """Count all active users"""
        try:
            query = "SELECT COUNT(*) as count FROM users WHERE is_active = 1"
            results = await txn.execute(query)
            if results:
                return results[0]["count"]
            return 0
        except Exception as e:
            raise Exception(f"Error counting active users: {e}")

    async def search_users(self, txn: ITransaction, query: str) -> List[UserType]:
        """Search users by name or CPF/CNPJ"""
        try:
            sql = """
            SELECT id, username, email, ms_oid, full_name, first_name, last_name, manager, unit, job, branche, cpf_cnpj, registration_number, profile_picture_url, is_active, created_at, updated_at 
            FROM users 
            WHERE (full_name LIKE :q OR cpf_cnpj LIKE :q OR username LIKE :q) AND is_active = 1
            """
            results = await txn.execute(sql, {"q": f"%{query}%"})
            return [UserType(**data) for data in results]
        except Exception as e:
            raise Exception(f"Error searching users: {e}")
