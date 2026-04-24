import json
from typing import List
from core.ports.repository import IApplicationRepository
from core.ports.infrastructure import ITransaction
from core.models.application_models import (
    ApplicationModel,
    ApplicationCreateModel,
    ApplicationUpdateModel,
    UserApplicationModel,
    UserApplicationCreateModel,
    UserWithPermissionsModel,
)
from core.helpers.sql_helper import filter_valid_update_clauses


class ApplicationRepository(IApplicationRepository):
    async def create_application(
        self, txn: ITransaction, app_data: ApplicationCreateModel
    ) -> ApplicationModel:
        """Create a new application"""
        try:
            data = app_data.model_dump()
            if data.get("permissions"):
                data["permissions"] = json.dumps(data["permissions"])

            query = """
            INSERT INTO applications (name, uri, type, description, permissions, is_active) 
            VALUES (:name, :uri, :type, :description, :permissions, :is_active)
            """
            await txn.execute(query, data)

            results = await txn.execute("SELECT LAST_INSERT_ID() as id")
            app_id = results[0]["id"]

            app = await self.get_application_by_id(txn, app_id)
            if app is None:
                raise Exception(
                    "Error creating application: Application not found after creation"
                )
            return app
        except Exception as e:
            raise Exception(f"Error creating application: {e}")

    async def get_application_by_id(
        self, txn: ITransaction, app_id: int
    ) -> ApplicationModel | None:
        """Get application by ID"""
        try:
            query = """
            SELECT id, name, uri, type, description, permissions, is_active, created_at, updated_at 
            FROM applications 
            WHERE id = :id
            """
            results = await txn.execute(query, {"id": app_id})
            if results:
                data = dict(results[0])
                if data.get("permissions") and isinstance(data["permissions"], str):
                    data["permissions"] = json.loads(data["permissions"])
                return ApplicationModel(**data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching application by ID: {e}")

    async def get_application_by_name(
        self, txn: ITransaction, name: str
    ) -> ApplicationModel | None:
        """Get application by name"""
        try:
            query = """
            SELECT id, name, uri, type, description, permissions, is_active, created_at, updated_at 
            FROM applications 
            WHERE name = :name
            """
            results = await txn.execute(query, {"name": name})
            if results:
                data = dict(results[0])
                if data.get("permissions") and isinstance(data["permissions"], str):
                    data["permissions"] = json.loads(data["permissions"])
                return ApplicationModel(**data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching application by name: {e}")

    async def list_applications(self, txn: ITransaction) -> List[ApplicationModel]:
        """List all applications"""
        try:
            query = """
            SELECT id, name, uri, type, description, permissions, is_active, created_at, updated_at 
            FROM applications
            """
            results = await txn.execute(query)
            final_results = []
            for row in results:
                data = dict(row)
                if data.get("permissions") and isinstance(data["permissions"], str):
                    data["permissions"] = json.loads(data["permissions"])
                final_results.append(ApplicationModel(**data))
            return final_results
        except Exception as e:
            raise Exception(f"Error listing applications: {e}")

    async def update_application(
        self, txn: ITransaction, app_id: int, app_data: ApplicationUpdateModel
    ) -> ApplicationModel:
        """Update an existing application"""
        try:
            fields = app_data.model_dump(exclude_unset=True)
            if not fields:
                app = await self.get_application_by_id(txn, app_id)
                if app is None:
                    raise Exception("Application not found")
                return app

            if "permissions" in fields and fields["permissions"] is not None:
                fields["permissions"] = json.dumps(fields["permissions"])

            set_clause, params = filter_valid_update_clauses(fields, app_id)

            query = f"""
            UPDATE applications
            SET {set_clause}, updated_at = NOW()
            WHERE id = :id
            """
            await txn.execute(query, params)

            up_app = await self.get_application_by_id(txn, app_id)
            if up_app is None:
                raise Exception("Application not found after update")
            return up_app
        except Exception as e:
            raise Exception(f"Error updating application: {e}")

    async def delete_application(self, txn: ITransaction, app_id: int) -> None:
        """Soft delete an application by ID"""
        try:
            query = "UPDATE applications SET is_active = 0 WHERE id = :id"
            await txn.execute(query, {"id": app_id})
        except Exception as e:
            raise Exception(f"Error deleting application: {e}")

    async def link_user_to_application(
        self, txn: ITransaction, link_data: UserApplicationCreateModel
    ) -> UserApplicationModel:
        """Link a user to an application with permissions"""
        try:
            check_query = "SELECT id FROM user_applications WHERE user_id = :user_id AND application_id = :application_id"
            check_results = await txn.execute(
                check_query,
                {
                    "user_id": link_data.user_id,
                    "application_id": link_data.application_id,
                },
            )

            permissions_json = json.dumps(link_data.permissions)

            if check_results:
                query = """
                UPDATE user_applications 
                SET permissions = :permissions, updated_at = NOW() 
                WHERE user_id = :user_id AND application_id = :application_id
                """
            else:
                query = """
                INSERT INTO user_applications (user_id, application_id, permissions) 
                VALUES (:user_id, :application_id, :permissions)
                """

            await txn.execute(
                query,
                {
                    "user_id": link_data.user_id,
                    "application_id": link_data.application_id,
                    "permissions": permissions_json,
                },
            )

            user_app: UserApplicationModel | None = await self.get_user_permissions(
                txn, link_data.user_id, link_data.application_id
            )

            if not user_app:
                raise Exception("User not found")

            return user_app
        except Exception as e:
            raise Exception(f"Error linking user to application: {e}")

    async def unlink_user_from_application(
        self, txn: ITransaction, user_id: int, app_id: int
    ) -> None:
        """Unlink a user from an application"""
        try:
            query = "DELETE FROM user_applications WHERE user_id = :user_id AND application_id = :app_id"
            await txn.execute(query, {"user_id": user_id, "app_id": app_id})
        except Exception as e:
            raise Exception(f"Error unlinking user from application: {e}")

    async def get_user_permissions(
        self, txn: ITransaction, user_id: int, app_id: int
    ) -> UserApplicationModel | None:
        """Get user permissions for a specific application"""
        try:
            query = """
            SELECT id, user_id, application_id, permissions, created_at, updated_at 
            FROM user_applications 
            WHERE user_id = :user_id AND application_id = :app_id
            """
            results = await txn.execute(query, {"user_id": user_id, "app_id": app_id})
            if results:
                data = dict(results[0])
                if isinstance(data["permissions"], str):
                    data["permissions"] = json.loads(data["permissions"])
                return UserApplicationModel(**data)
            return None
        except Exception as e:
            raise Exception(f"Error fetching user permissions: {e}")

    async def list_user_applications(
        self, txn: ITransaction, user_id: int
    ) -> List[ApplicationModel]:
        """List all applications linked to a specific user"""
        try:
            query = """
            SELECT a.id, a.name, a.uri, a.type, a.description, a.permissions, a.is_active, a.created_at, a.updated_at 
            FROM applications a
            JOIN user_applications ua ON a.id = ua.application_id
            WHERE ua.user_id = :user_id
            """
            results = await txn.execute(query, {"user_id": user_id})
            final_results = []
            for row in results:
                data = dict(row)
                if data.get("permissions") and isinstance(data["permissions"], str):
                    data["permissions"] = json.loads(data["permissions"])
                final_results.append(ApplicationModel(**data))
            return final_results
        except Exception as e:
            raise Exception(f"Error listing user applications: {e}")

    async def get_application_users_permissions(
        self, txn: ITransaction, app_id: int
    ) -> List[UserWithPermissionsModel]:
        """Get all users and their permissions for a specific application"""
        try:
            query = """
            SELECT u.id as user_id, u.username, u.email, ua.permissions
            FROM users u
            JOIN user_applications ua ON u.id = ua.user_id
            WHERE ua.application_id = :app_id
            """
            results = await txn.execute(query, {"app_id": app_id})
            final_results = []
            for row in results:
                data = dict(row)
                if isinstance(data["permissions"], str):
                    data["permissions"] = json.loads(data["permissions"])
                final_results.append(UserWithPermissionsModel(**data))
            return final_results
        except Exception as e:
            raise Exception(f"Error fetching application users permissions: {e}")
