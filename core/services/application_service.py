from typing import List
from core.ports.service import IApplicationService
from core.ports.repository import IApplicationRepository
from core.ports.infrastructure import IDatabase
from core.models.application_models import (
    ApplicationModel,
    ApplicationCreateModel,
    ApplicationUpdateModel,
    UserApplicationModel,
    UserApplicationCreateModel,
    UserApplicationUpdateModel,
    UserWithPermissionsModel,
    UserApplicationDetailModel,
    ApplicationType,
)


class ApplicationService(IApplicationService):
    def __init__(self, application_repository: IApplicationRepository, db: IDatabase):
        self.application_repository: IApplicationRepository = application_repository
        self.db: IDatabase = db

    async def create_application(
        self, app_data: ApplicationCreateModel
    ) -> ApplicationModel:
        try:
            async with self.db.transaction() as txn:
                existing = await self.application_repository.get_application_by_name(
                    txn, app_data.name
                )
                if existing:
                    raise ValueError(
                        f"Application with name '{app_data.name}' already exists"
                    )

                return await self.application_repository.create_application(
                    txn, app_data
                )
        except Exception as e:
            raise Exception(f"Error in service layer while creating application: {e}")

    async def get_application_by_id(self, app_id: int) -> ApplicationModel:
        try:
            async with self.db.transaction() as txn:
                app = await self.application_repository.get_application_by_id(
                    txn, app_id
                )
                if not app:
                    raise ValueError(f"Application with ID {app_id} not found")
                return app
        except Exception as e:
            raise Exception(
                f"Error in service layer while fetching application by ID: {e}"
            )

    async def list_applications(self) -> List[ApplicationModel]:
        try:
            async with self.db.transaction() as txn:
                return await self.application_repository.list_applications(txn)
        except Exception as e:
            raise Exception(f"Error in service layer while listing applications: {e}")

    async def update_application(
        self, app_id: int, app_data: ApplicationUpdateModel
    ) -> ApplicationModel:
        try:
            async with self.db.transaction() as txn:
                app = await self.application_repository.get_application_by_id(
                    txn, app_id
                )
                if not app:
                    raise ValueError(f"Application with ID {app_id} not found")

                if app_data.name and app_data.name != app.name:
                    existing = (
                        await self.application_repository.get_application_by_name(
                            txn, app_data.name
                        )
                    )
                    if existing:
                        raise ValueError(
                            f"Application with name '{app_data.name}' already exists"
                        )

                return await self.application_repository.update_application(
                    txn, app_id, app_data
                )
        except Exception as e:
            raise Exception(f"Error in service layer while updating application: {e}")

    async def delete_application(self, app_id: int) -> None:
        try:
            async with self.db.transaction() as txn:
                app = await self.application_repository.get_application_by_id(
                    txn, app_id
                )
                if not app:
                    raise ValueError(f"Application with ID {app_id} not found")

                await self.application_repository.delete_application(txn, app_id)
        except Exception as e:
            raise Exception(f"Error in service layer while deleting application: {e}")

    async def link_user_to_application(
        self, link_data: UserApplicationCreateModel
    ) -> UserApplicationModel:
        try:
            async with self.db.transaction() as txn:
                app = await self.application_repository.get_application_by_id(
                    txn, link_data.application_id
                )
                if not app:
                    raise ValueError(
                        f"Application with ID {link_data.application_id} not found"
                    )

                return await self.application_repository.link_user_to_application(
                    txn, link_data
                )
        except Exception as e:
            raise Exception(
                f"Error in service layer while linking user to application: {e}"
            )

    async def unlink_user_from_application(self, user_id: int, app_id: int) -> None:
        try:
            async with self.db.transaction() as txn:
                await self.application_repository.unlink_user_from_application(
                    txn, user_id, app_id
                )
        except Exception as e:
            raise Exception(
                f"Error in service layer while unlinking user from application: {e}"
            )

    async def update_user_permissions(
        self, user_id: int, app_id: int, permissions: UserApplicationUpdateModel
    ) -> UserApplicationModel:
        try:
            async with self.db.transaction() as txn:
                link_data = UserApplicationCreateModel(
                    user_id=user_id,
                    application_id=app_id,
                    permissions=permissions.permissions,
                )
                return await self.application_repository.link_user_to_application(
                    txn, link_data
                )
        except Exception as e:
            raise Exception(
                f"Error in service layer while updating user permissions: {e}"
            )

    async def get_user_permissions(
        self, user_id: int, app_id: int
    ) -> UserApplicationModel:
        try:
            async with self.db.transaction() as txn:
                permissions = await self.application_repository.get_user_permissions(
                    txn, user_id, app_id
                )
                if not permissions:
                    raise ValueError(
                        f"User {user_id} does not have specific permissions for application {app_id}"
                    )
                return permissions
        except Exception as e:
            raise Exception(
                f"Error in service layer while fetching user permissions: {e}"
            )

    async def list_user_applications(self, user_id: int) -> List[ApplicationModel]:
        try:
            async with self.db.transaction() as txn:
                linked_apps = await self.application_repository.list_user_applications(
                    txn, user_id
                )
                all_apps = await self.application_repository.list_applications(txn)
                public_apps = [
                    a for a in all_apps if a.type == ApplicationType.ALL and a.is_active
                ]

                linked_ids = {a.id for a in linked_apps}
                for app in public_apps:
                    if app.id not in linked_ids:
                        linked_apps.append(app)

                return linked_apps
        except Exception as e:
            raise Exception(
                f"Error in service layer while listing user applications: {e}"
            )

    async def get_application_users_permissions(
        self, app_id: int
    ) -> List[UserWithPermissionsModel]:
        try:
            async with self.db.transaction() as txn:
                return (
                    await self.application_repository.get_application_users_permissions(
                        txn, app_id
                    )
                )
        except Exception as e:
            raise Exception(
                f"Error in service layer while fetching application users permissions: {e}"
            )

    async def get_application_permissions(self, app_id: int) -> List[str]:
        try:
            async with self.db.transaction() as txn:
                app = await self.application_repository.get_application_by_id(
                    txn, app_id
                )
                if not app:
                    raise ValueError(f"Application with ID {app_id} not found")
                return app.permissions or []
        except Exception as e:
            raise Exception(
                f"Error in service layer while fetching application permissions: {e}"
            )

    async def check_user_access(self, user_id: int, app_id: int) -> bool:
        try:
            async with self.db.transaction() as txn:
                app = await self.application_repository.get_application_by_id(
                    txn, app_id
                )
                if not app or not app.is_active:
                    return False

                if app.type == ApplicationType.ALL:
                    return True

                permissions = await self.application_repository.get_user_permissions(
                    txn, user_id, app_id
                )
                return permissions is not None
        except Exception as e:
            raise Exception(f"Error in service layer while checking user access: {e}")

    async def get_available_users(
        self, app_id: int, search_query: str = ""
    ) -> List[UserWithPermissionsModel]:
        try:
            async with self.db.transaction() as txn:
                return await self.application_repository.get_users_not_in_application(
                    txn, app_id, search_query
                )
        except Exception as e:
            raise Exception(
                f"Error in service layer while fetching available users: {e}"
            )

    async def bulk_link_users(self, app_id: int, search_query: str = "") -> int:
        try:
            async with self.db.transaction() as txn:
                return await self.application_repository.bulk_link_all_users(
                    txn, app_id, search_query
                )
        except Exception as e:
            raise Exception(f"Error in service layer while bulk linking users: {e}")

    async def bulk_unlink_users(self, app_id: int) -> int:
        try:
            async with self.db.transaction() as txn:
                return await self.application_repository.bulk_unlink_all_users(
                    txn, app_id
                )
        except Exception as e:
            raise Exception(f"Error in service layer while bulk unlinking users: {e}")

    async def list_user_applications_with_permissions(
        self, user_id: int
    ) -> List[UserApplicationDetailModel]:
        """List all applications and permissions linked to a specific user"""
        try:
            async with self.db.transaction() as txn:
                return (
                    await self.application_repository.list_user_applications_with_permissions(
                        txn, user_id
                    )
                )
        except Exception as e:
            raise Exception(
                f"Error in service layer while listing user applications with permissions: {e}"
            )
