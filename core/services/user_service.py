from typing import List
from core.repositories.user_repository import IUserRepository
from core.ports.service import IUserService
from core.models.user_models import UserCreateType, UserUpdateType, UserType


class UserService(IUserService):
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    async def get_user_by_username(self, username: str) -> UserType:
        return await self.user_repository.get_user_by_username(username)

    async def get_user_by_id(self, user_id: int) -> UserType:
        return await self.user_repository.get_user_by_id(user_id)

    async def get_user_hashed_password(self, username: str) -> str:
        return await self.user_repository.get_user_hashed_password(username)

    async def create_user(
        self, user_data: UserCreateType, hashed_password: str
    ) -> UserType:
        return await self.user_repository.create_user(user_data, hashed_password)

    async def list_users(self) -> List[UserType]:
        return await self.user_repository.list_users()

    async def update_user(self, user_id: int, user_data: UserUpdateType) -> UserType:
        return await self.user_repository.update_user(user_id, user_data)

    async def update_user_password(self, user_id: int, hashed_password: str) -> None:
        return await self.user_repository.update_user_password(user_id, hashed_password)

    async def delete_user(self, user_id: int) -> None:
        return await self.user_repository.delete_user(user_id)
