from typing import List

from core.models.user_models import UserUpdatePasswordType
from core.models.user_models import UserCreateType, UserUpdateType, UserType

from core.repositories.user_repository import IUserRepository
from core.ports.service import IUserService
from core.ports.infrastructure import IDatabase
from core.helpers.authentication_helper import verify_password, get_password_hash


class UserService(IUserService):
    def __init__(self, user_repository: IUserRepository, db: IDatabase):
        self.user_repository: IUserRepository = user_repository
        self.db: IDatabase = db

    async def get_user_by_cpfcnpj(self, cpf_cnpj: str) -> UserType:
        try:
            async with self.db.transaction() as txn:
                user: UserType | None = await self.user_repository.get_user_by_cpfcnpj(
                    txn, cpf_cnpj
                )
                if not user:
                    raise ValueError("User not found")
                return user
        except Exception as e:
            raise Exception(
                f"Error in service layer while fetching user by CPF/CNPJ: {e}"
            )

    async def get_user_by_email(self, email: str) -> UserType:
        try:
            async with self.db.transaction() as txn:
                user: UserType | None = await self.user_repository.get_user_by_email(
                    txn, email
                )
                if not user:
                    raise ValueError("User not found")
                return user
        except Exception as e:
            raise Exception(f"Error in service layer while fetching user by email: {e}")

    async def get_user_by_id(self, user_id: int) -> UserType:
        try:
            async with self.db.transaction() as txn:
                user: UserType | None = await self.user_repository.get_user_by_id(
                    txn, user_id
                )
                if not user:
                    raise ValueError("User not found")
                return user
        except Exception as e:
            raise Exception(f"Error in service layer while fetching user by id: {e}")

    async def get_user_hashed_password(self, email: str) -> str:
        try:
            async with self.db.transaction() as txn:
                hashed_password: (
                    str | None
                ) = await self.user_repository.get_user_hashed_password(txn, email)
                if not hashed_password:
                    raise ValueError("User not found or password not set")
                return hashed_password
        except Exception as e:
            raise Exception(
                f"Error in service layer while fetching user hashed password: {e}"
            )

    async def create_user(self, user_data: UserCreateType) -> UserType:
        try:
            # Safe check for required fields
            verified: UserCreateType = UserCreateType.model_validate(user_data)

            async with self.db.transaction() as txn:
                # Safe checks for existing user by CPF/CNPJ and email to prevent duplicates
                cpf_cnpj_user: (
                    UserType | None
                ) = await self.user_repository.get_user_by_cpfcnpj(
                    txn, verified.cpf_cnpj
                )
                if cpf_cnpj_user:
                    raise ValueError("User already exists")
                email_user: (
                    UserType | None
                ) = await self.user_repository.get_user_by_email(txn, verified.email)
                if email_user:
                    raise ValueError("User already exists")

                if not verified.password:
                    raise ValueError("Password is required")

                hashed_password: str = get_password_hash(verified.password)
                user: UserType = await self.user_repository.create_user(
                    txn, verified, hashed_password
                )
                return user
        except Exception as e:
            raise Exception(f"Error in service layer while creating user: {e}")

    async def list_users(self) -> List[UserType]:
        try:
            async with self.db.transaction() as txn:
                users: List[UserType] = await self.user_repository.list_users(txn)
                return users
        except Exception as e:
            raise Exception(f"Error in service layer while listing users: {e}")

    async def update_user(self, user_id: int, user_data: UserUpdateType) -> UserType:
        try:
            async with self.db.transaction() as txn:
                user: UserType | None = await self.user_repository.get_user_by_id(
                    txn, user_id
                )
                if not user:
                    raise ValueError("User not found")

                verified: UserUpdateType = UserUpdateType.model_validate(user_data)

                # Enforcement: If user is from SGA, lock certain fields
                if user.registration_number:
                    # We create a new UserUpdateType from the model dump but EXCLUDING the locked fields
                    # to ensure we don't accidentally update them even if provided in the payload.
                    locked_fields = {
                        "full_name",
                        "first_name",
                        "last_name",
                        "cpf_cnpj",
                        "unit",
                        "job",
                        "branche",
                        "registration_number",
                    }
                    update_data = verified.model_dump(exclude_unset=True)
                    for field in locked_fields:
                        update_data.pop(field, None)

                    # If after popping there's nothing left to update, just return the user
                    if not update_data:
                        return user

                    verified = UserUpdateType(**update_data)

                if verified.cpf_cnpj and verified.cpf_cnpj != user.cpf_cnpj:
                    existing_user: (
                        UserType | None
                    ) = await self.user_repository.get_user_by_cpfcnpj(
                        txn, verified.cpf_cnpj
                    )
                    if existing_user:
                        raise ValueError("CPF/CNPJ already exists")

                if verified.email and verified.email != user.email:
                    existing_user: (
                        UserType | None
                    ) = await self.user_repository.get_user_by_email(
                        txn, verified.email
                    )
                    if existing_user:
                        raise ValueError("Email already exists")

                updated_user: UserType = await self.user_repository.update_user(
                    txn, user_id, verified
                )
                return updated_user
        except Exception as e:
            raise Exception(f"Error in service layer while updating user: {e}")

    async def update_user_password(
        self, user_id: int, passwords_data: UserUpdatePasswordType
    ) -> None:
        try:
            async with self.db.transaction() as txn:
                user: UserType | None = await self.user_repository.get_user_by_id(
                    txn, user_id
                )
                if not user:
                    raise ValueError("User not found")

                if (
                    not passwords_data.new_password
                    or not passwords_data.current_password
                ):
                    raise ValueError("New password and current password are required")

                if not user.cpf_cnpj:
                    raise ValueError("User CPF/CNPJ not found")

                hashed_password: (
                    str | None
                ) = await self.user_repository.get_user_hashed_password(
                    txn, user.cpf_cnpj
                )

                if not hashed_password or not verify_password(
                    passwords_data.current_password, hashed_password
                ):
                    raise ValueError("Current password is incorrect")

                hashed_new_password: str = get_password_hash(
                    passwords_data.new_password
                )
                await self.user_repository.update_user_password(
                    txn, user.id, hashed_new_password
                )
        except Exception as e:
            raise Exception(f"Error in service layer while updating user password: {e}")

    async def is_user_admin(self, cpf_cnpj: str) -> bool:
        """Check if the user with the given CPF/CNPJ is an admin"""
        try:
            async with self.db.transaction() as txn:
                is_admin: bool = await self.user_repository.is_user_admin(txn, cpf_cnpj)
                return is_admin
        except Exception as e:
            raise Exception(
                f"Error in service layer while checking if user is admin: {e}"
            )

    async def reset_user_password(self, user_email: str, new_password: str) -> None:
        try:
            async with self.db.transaction() as txn:
                user: UserType | None = await self.user_repository.get_user_by_email(
                    txn, user_email
                )
                if not user:
                    raise ValueError("User not found")
                hashed_new_password: str = get_password_hash(new_password)
                await self.user_repository.update_user_password(
                    txn, user.id, hashed_new_password
                )
        except Exception as e:
            raise Exception(
                f"Error in service layer while resetting user password: {e}"
            )

    async def delete_user(self, user_id: int) -> None:
        try:
            async with self.db.transaction() as txn:
                user: UserType | None = await self.user_repository.get_user_by_id(
                    txn, user_id
                )
                if not user:
                    raise ValueError("User not found")
                await self.user_repository.delete_user(txn, user_id)
        except Exception as e:
            raise Exception(f"Error in service layer while deleting user: {e}")

    async def count_active_users(self) -> int:
        try:
            async with self.db.transaction() as txn:
                return await self.user_repository.count_active_users(txn)
        except Exception as e:
            raise Exception(f"Error in service layer while counting active users: {e}")

    async def search_users(self, query: str) -> List[UserType]:
        """Search users by name or CPF/CNPJ"""
        try:
            async with self.db.transaction() as txn:
                return await self.user_repository.search_users(txn, query)
        except Exception as e:
            raise Exception(f"Error in service layer while searching users: {e}")
