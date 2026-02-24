from typing import List

from core.models.user_models import UserUpdatePasswordType
from core.models.user_models import UserCreateType, UserUpdateType, UserType

from core.repositories.user_repository import IUserRepository
from core.ports.service import IUserService
from core.helpers.authentication_helper import verify_password, get_password_hash


class UserService(IUserService):
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    async def get_user_by_username(self, auth_user_id: int, username: str) -> UserType:
        try:
            user: UserType = await self.user_repository.get_user_by_username(username)
            if not user:
                raise ValueError("User not found")
            return user
        except Exception as e:
            raise Exception(
                f"Error in service layer while fetching user by username: {e}"
            )

    async def get_user_by_email(self, auth_user_id: int, email: str) -> UserType:
        try:
            user: UserType = await self.user_repository.get_user_by_email(email)
            if not user:
                raise ValueError("User not found")
            return user
        except Exception as e:
            raise Exception(f"Error in service layer while fetching user by email: {e}")

    async def get_user_by_id(self, auth_user_id: int, user_id: int) -> UserType:
        try:
            user: UserType = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            return user
        except Exception as e:
            raise Exception(f"Error in service layer while fetching user by id: {e}")

    async def get_user_hashed_password(self, auth_user_id: int, username: str) -> str:
        try:
            hashed_password: str = await self.user_repository.get_user_hashed_password(
                username
            )
            return hashed_password
        except Exception as e:
            raise Exception(
                f"Error in service layer while fetching user hashed password: {e}"
            )

    async def create_user(
        self, auth_user_id: int, user_data: UserCreateType
    ) -> UserType:
        try:
            in_user: UserType = await self.user_repository.get_user_by_username(
                user_data.username
            )
            if in_user or in_user.email == user_data.email:
                raise ValueError("User already exists")
            hashed_password: str = get_password_hash(user_data.password)
            user: UserType = await self.user_repository.create_user(
                user_data, hashed_password
            )
            return user
        except Exception as e:
            raise Exception(f"Error in service layer while creating user: {e}")

    async def list_users(self, auth_user_id: int) -> List[UserType]:
        try:
            users: List[UserType] = await self.user_repository.list_users()
            return users
        except Exception as e:
            raise Exception(f"Error in service layer while listing users: {e}")

    async def update_user(
        self, auth_user_id: int, user_id: int, user_data: UserUpdateType
    ) -> UserType:
        try:
            user: UserType = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            if user_data.username and user_data.username != user.username:
                user: UserType = await self.user_repository.get_user_by_username(
                    user_data.username
                )
                if user:
                    raise ValueError("User already exists")
            if user_data.email and user_data.email != user.email:
                user: UserType = await self.user_repository.get_user_by_email(
                    user_data.email
                )
                if user:
                    raise ValueError("User already exists")
            user: UserType = await self.user_repository.update_user(user_id, user_data)
            return user
        except Exception as e:
            raise Exception(f"Error in service layer while updating user: {e}")

    async def update_user_password(
        self, auth_user_id: int, user_id: int, passwords_data: UserUpdatePasswordType
    ) -> None:
        try:
            user: UserType = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            if not passwords_data.new_password or not passwords_data.current_password:
                raise ValueError("New password and current password are required")
            hashed_password: str = await self.user_repository.get_user_hashed_password(
                user.username
            )
            if not verify_password(passwords_data.current_password, hashed_password):
                raise ValueError("Current password is incorrect")
            await self.user_repository.update_user_password(
                user_id, passwords_data.new_password
            )
        except Exception as e:
            raise Exception(f"Error in service layer while updating user password: {e}")

    async def delete_user(self, auth_user_id: int, user_id: int) -> None:
        try:
            user: UserType = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            await self.user_repository.delete_user(user_id)
        except Exception as e:
            raise Exception(f"Error in service layer while deleting user: {e}")
