from typing import List

from core.models.user_models import UserUpdatePasswordType
from core.models.user_models import UserCreateType, UserUpdateType, UserType

from core.repositories.user_repository import IUserRepository
from core.ports.service import IUserService
from core.helpers.authentication_helper import verify_password, get_password_hash


class UserService(IUserService):
    def __init__(self, user_repository: IUserRepository):
        self.user_repository: IUserRepository = user_repository

    async def get_user_by_cpfcnpj(self, cpf_cnpj: str) -> UserType:
        try:
            user: UserType | None = await self.user_repository.get_user_by_cpfcnpj(
                cpf_cnpj
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
            user: UserType | None = await self.user_repository.get_user_by_email(email)
            if not user:
                raise ValueError("User not found")
            return user
        except Exception as e:
            raise Exception(f"Error in service layer while fetching user by email: {e}")

    async def get_user_by_id(self, user_id: int) -> UserType:
        try:
            user: UserType | None = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            return user
        except Exception as e:
            raise Exception(f"Error in service layer while fetching user by id: {e}")

    async def get_user_hashed_password(self, email: str) -> str:
        """
        This functions allow a future implementation of a password reset flow, where the user can request a password reset link, and the system can verify the user's email and send a reset link if the user exists. The function is not currently used in the code, but it is implemented in the service layer to allow for future expansion of the authentication features.
        """
        try:
            hashed_password: (
                str | None
            ) = await self.user_repository.get_user_hashed_password(email)
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

            # Safe checks for existing user by CPF/CNPJ and email to prevent duplicates
            cpf_cnpj_user: (
                UserType | None
            ) = await self.user_repository.get_user_by_cpfcnpj(verified.cpf_cnpj)
            if cpf_cnpj_user:
                raise ValueError("User already exists")
            email_user: UserType | None = await self.user_repository.get_user_by_email(
                verified.email
            )
            if email_user:
                raise ValueError("User already exists")
            if not verified.password:
                raise ValueError("Password is required")
            hashed_password: str = get_password_hash(verified.password)
            user: UserType = await self.user_repository.create_user(
                verified, hashed_password
            )
            return user
        except Exception as e:
            raise Exception(f"Error in service layer while creating user: {e}")

    async def list_users(self) -> List[UserType]:
        try:
            users: List[UserType] = await self.user_repository.list_users()
            return users
        except Exception as e:
            raise Exception(f"Error in service layer while listing users: {e}")

    async def update_user(self, user_id: int, user_data: UserUpdateType) -> UserType:
        try:
            user: UserType | None = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            verified: UserUpdateType = UserUpdateType.model_validate(user_data)
            if verified.cpf_cnpj and verified.cpf_cnpj != user.cpf_cnpj:
                existing_user: (
                    UserType | None
                ) = await self.user_repository.get_user_by_cpfcnpj(verified.cpf_cnpj)
                if existing_user:
                    raise ValueError("CPF/CNPJ already exists")
            if verified.email and verified.email != user.email:
                existing_user: (
                    UserType | None
                ) = await self.user_repository.get_user_by_email(verified.email)
                if existing_user:
                    raise ValueError("Email already exists")
            updated_user: UserType = await self.user_repository.update_user(
                user_id, verified
            )
            return updated_user
        except Exception as e:
            raise Exception(f"Error in service layer while updating user: {e}")

    async def update_user_password(
        self, user_id: int, passwords_data: UserUpdatePasswordType
    ) -> None:
        try:
            user: UserType | None = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            if not passwords_data.new_password or not passwords_data.current_password:
                raise ValueError("New password and current password are required")
            hashed_password: (
                str | None
            ) = await self.user_repository.get_user_hashed_password(user.email)
            if not hashed_password or not verify_password(
                passwords_data.current_password, hashed_password
            ):
                raise ValueError("Current password is incorrect")
            hashed_new_password: str = get_password_hash(passwords_data.new_password)
            await self.user_repository.update_user_password(
                user.id, hashed_new_password
            )
        except Exception as e:
            raise Exception(f"Error in service layer while updating user password: {e}")

    async def is_user_admin(self, cpf_cnpj: str) -> bool:
        """Check if the user with the given CPF/CNPJ is an admin"""
        try:
            is_admin: bool = await self.user_repository.is_user_admin(cpf_cnpj)
            return is_admin
        except Exception as e:
            raise Exception(
                f"Error in service layer while checking if user is admin: {e}"
            )

    async def reset_user_password(self, user_email: str, new_password: str) -> None:
        try:
            user: UserType | None = await self.user_repository.get_user_by_email(
                user_email
            )
            if not user:
                raise ValueError("User not found")
            hashed_new_password: str = get_password_hash(new_password)
            await self.user_repository.update_user_password(
                user.id, hashed_new_password
            )
        except Exception as e:
            raise Exception(
                f"Error in service layer while resetting user password: {e}"
            )

    async def delete_user(self, user_id: int) -> None:
        try:
            user: UserType | None = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            await self.user_repository.delete_user(user_id)
        except Exception as e:
            raise Exception(f"Error in service layer while deleting user: {e}")
