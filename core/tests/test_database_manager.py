"""
Unit tests for DatabaseManager, MariaDbAdapter / MariaDbTransaction,
and SqlServerAdapter / SqlServerTransaction.

All external I/O (SQLAlchemy engine, pyodbc) is fully mocked —
no real database is required to run this suite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.infrastructure.database_manager import DatabaseManager
from core.infrastructure.mariadb_adapter import MariaDbAdapter, MariaDbTransaction
from core.infrastructure.sqls_adapter import SqlServerAdapter, SqlServerTransaction


# ─── helpers ──────────────────────────────────────────────────────────────────

def _async_ctx(value=None):
    """Returns a MagicMock that behaves as an async context manager."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=value)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ─── DatabaseManager ──────────────────────────────────────────────────────────

class TestDatabaseManager:

    @pytest.fixture
    def manager(self):
        return DatabaseManager()

    # --- registration & retrieval ---

    @pytest.mark.asyncio
    async def test_register_and_get_returns_same_instance(self, manager):
        db = AsyncMock()
        await manager.register("mydb", db)
        assert await manager.get("mydb") is db

    @pytest.mark.asyncio
    async def test_get_unregistered_raises_value_error(self, manager):
        with pytest.raises(ValueError, match="not registered"):
            await manager.get("ghost")

    @pytest.mark.asyncio
    async def test_register_overwrite_replaces_previous(self, manager):
        db_old, db_new = AsyncMock(), AsyncMock()
        await manager.register("db", db_old)
        await manager.register("db", db_new)
        assert await manager.get("db") is db_new

    # --- shutdown ---

    @pytest.mark.asyncio
    async def test_shutdown_calls_disconnect_on_every_database(self, manager):
        db1, db2 = AsyncMock(), AsyncMock()
        await manager.register("a", db1)
        await manager.register("b", db2)
        await manager.shutdown()
        db1.disconnect.assert_awaited_once()
        db2.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_tolerates_disconnect_error(self, manager):
        db = AsyncMock()
        db.disconnect.side_effect = RuntimeError("network gone")
        await manager.register("db", db)
        await manager.shutdown()  # must not propagate the error

    # --- health check ---

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, manager):
        mock_txn = AsyncMock()
        db = AsyncMock()
        db.transaction = MagicMock(return_value=_async_ctx(mock_txn))
        await manager.register("db", db)

        results = await manager.health_check()

        assert results["db"]["status"] == "healthy"
        mock_txn.execute.assert_awaited_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_transaction_error(self, manager):
        db = AsyncMock()
        db.transaction = MagicMock(side_effect=RuntimeError("connection refused"))
        await manager.register("db", db)

        results = await manager.health_check()

        assert results["db"]["status"] == "unhealthy"
        assert "connection refused" in results["db"]["error"]

    @pytest.mark.asyncio
    async def test_health_check_reports_all_databases(self, manager):
        healthy_txn = AsyncMock()
        db_ok = AsyncMock()
        db_ok.transaction = MagicMock(return_value=_async_ctx(healthy_txn))

        db_bad = AsyncMock()
        db_bad.transaction = MagicMock(side_effect=RuntimeError("down"))

        await manager.register("ok", db_ok)
        await manager.register("bad", db_bad)
        results = await manager.health_check()

        assert results["ok"]["status"] == "healthy"
        assert results["bad"]["status"] == "unhealthy"


# ─── MariaDbTransaction ────────────────────────────────────────────────────────

class TestMariaDbTransaction:

    def _conn_with_result(self, rows: list[dict], returns_rows: bool = True):
        mock_result = MagicMock()
        mock_result.returns_rows = returns_rows
        mock_result.all.return_value = [MagicMock(_mapping=row) for row in rows]
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_result)
        return mock_conn

    @pytest.mark.asyncio
    async def test_execute_returns_mapped_rows(self):
        mock_conn = self._conn_with_result([{"id": 1, "name": "Alice"}])
        txn = MariaDbTransaction(mock_conn)
        rows = await txn.execute("SELECT * FROM users")
        assert rows == [{"id": 1, "name": "Alice"}]

    @pytest.mark.asyncio
    async def test_execute_non_returning_query_returns_empty(self):
        mock_conn = self._conn_with_result([], returns_rows=False)
        txn = MariaDbTransaction(mock_conn)
        rows = await txn.execute("UPDATE users SET active=1")
        assert rows == []

    @pytest.mark.asyncio
    async def test_execute_passes_params(self):
        mock_conn = self._conn_with_result([])
        txn = MariaDbTransaction(mock_conn)
        await txn.execute("SELECT * FROM users WHERE id = :id", {"id": 1})
        mock_conn.execute.assert_awaited_once()
        _, call_kwargs = mock_conn.execute.call_args
        # params forwarded as second positional arg
        assert mock_conn.execute.call_args[0][1] == {"id": 1}

    @pytest.mark.asyncio
    async def test_commit_delegates_to_connection(self):
        mock_conn = AsyncMock()
        await MariaDbTransaction(mock_conn).commit()
        mock_conn.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rollback_delegates_to_connection(self):
        mock_conn = AsyncMock()
        await MariaDbTransaction(mock_conn).rollback()
        mock_conn.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_last_insert_id_returns_scalar(self):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_result)
        result = await MariaDbTransaction(mock_conn).last_insert_id()
        assert result == 42

    @pytest.mark.asyncio
    async def test_last_insert_id_returns_zero_when_none(self):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = None
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_result)
        result = await MariaDbTransaction(mock_conn).last_insert_id()
        assert result == 0


# ─── MariaDbAdapter ────────────────────────────────────────────────────────────

class TestMariaDbAdapter:

    _CONN_STR = "mariadb+asyncmy://user:pass@localhost/db"

    @patch("core.infrastructure.mariadb_adapter.create_async_engine")
    def test_init_accepts_valid_connection_string(self, mock_factory):
        MariaDbAdapter(self._CONN_STR)
        mock_factory.assert_called_once()

    @patch("core.infrastructure.mariadb_adapter.create_async_engine")
    def test_validate_raises_on_wrong_prefix(self, _):
        with pytest.raises(ValueError, match="mariadb\\+"):
            MariaDbAdapter("mysql+asyncmy://user:pass@localhost/db")

    @pytest.mark.asyncio
    @patch("core.infrastructure.mariadb_adapter.create_async_engine")
    async def test_transaction_yields_mariadb_transaction(self, mock_factory):
        mock_conn = AsyncMock()
        mock_conn.begin = MagicMock(return_value=_async_ctx())
        mock_factory.return_value = MagicMock(
            connect=MagicMock(return_value=_async_ctx(mock_conn))
        )

        adapter = MariaDbAdapter(self._CONN_STR)
        async with adapter.transaction() as txn:
            assert isinstance(txn, MariaDbTransaction)

    @pytest.mark.asyncio
    @patch("core.infrastructure.mariadb_adapter.create_async_engine")
    async def test_transaction_propagates_exception(self, mock_factory):
        mock_conn = AsyncMock()
        mock_conn.begin = MagicMock(return_value=_async_ctx())
        mock_factory.return_value = MagicMock(
            connect=MagicMock(return_value=_async_ctx(mock_conn))
        )

        adapter = MariaDbAdapter(self._CONN_STR)
        with pytest.raises(RuntimeError, match="db error"):
            async with adapter.transaction():
                raise RuntimeError("db error")

    @pytest.mark.asyncio
    @patch("core.infrastructure.mariadb_adapter.create_async_engine")
    async def test_disconnect_disposes_engine(self, mock_factory):
        mock_engine = AsyncMock()
        mock_factory.return_value = mock_engine

        adapter = MariaDbAdapter(self._CONN_STR)
        await adapter.disconnect()
        mock_engine.dispose.assert_awaited_once()


# ─── SqlServerTransaction ──────────────────────────────────────────────────────

class TestSqlServerTransaction:

    def _make_conn(self, description, rows):
        cursor = MagicMock()
        cursor.description = description
        cursor.fetchall.return_value = rows
        conn = MagicMock()
        conn.cursor.return_value = cursor
        return conn, cursor

    @pytest.mark.asyncio
    async def test_execute_returns_mapped_rows(self):
        conn, _ = self._make_conn(
            description=[("id",), ("name",)],
            rows=[(1, "Alice"), (2, "Bob")],
        )
        rows = await SqlServerTransaction(conn).execute("SELECT id, name FROM users")
        assert rows == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    @pytest.mark.asyncio
    async def test_execute_non_returning_query_returns_empty(self):
        conn, _ = self._make_conn(description=None, rows=[])
        rows = await SqlServerTransaction(conn).execute("DELETE FROM users WHERE id=1")
        assert rows == []

    @pytest.mark.asyncio
    async def test_execute_always_closes_cursor_on_success(self):
        conn, cursor = self._make_conn(description=None, rows=[])
        await SqlServerTransaction(conn).execute("DELETE FROM users WHERE id=1")
        cursor.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_always_closes_cursor_on_error(self):
        cursor = MagicMock()
        cursor.execute.side_effect = Exception("boom")
        conn = MagicMock()
        conn.cursor.return_value = cursor

        with pytest.raises(Exception, match="boom"):
            await SqlServerTransaction(conn).execute("SELECT 1")
        cursor.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_calls_conn_commit(self):
        conn = MagicMock()
        await SqlServerTransaction(conn).commit()
        conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_calls_conn_rollback(self):
        conn = MagicMock()
        await SqlServerTransaction(conn).rollback()
        conn.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_last_insert_id_returns_value(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (99,)
        conn = MagicMock()
        conn.cursor.return_value = cursor
        result = await SqlServerTransaction(conn).last_insert_id()
        assert result == 99

    @pytest.mark.asyncio
    async def test_last_insert_id_returns_zero_when_none(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (None,)
        conn = MagicMock()
        conn.cursor.return_value = cursor
        result = await SqlServerTransaction(conn).last_insert_id()
        assert result == 0


# ─── SqlServerAdapter ──────────────────────────────────────────────────────────

class TestSqlServerAdapter:

    _CONN_STR = "DRIVER={SQL Server};SERVER=localhost;DATABASE=mydb"

    def test_validate_empty_string_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            SqlServerAdapter("")

    def test_validate_missing_database_raises(self):
        with pytest.raises(ValueError, match="missing required parts"):
            SqlServerAdapter("DRIVER={SQL Server};SERVER=localhost")

    def test_validate_missing_server_raises(self):
        with pytest.raises(ValueError, match="missing required parts"):
            SqlServerAdapter("DRIVER={ODBC Driver 17};DATABASE=mydb")

    @pytest.mark.asyncio
    @patch("pyodbc.connect")
    async def test_transaction_commits_on_success(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        adapter = SqlServerAdapter(self._CONN_STR)
        async with adapter.transaction() as txn:
            assert isinstance(txn, SqlServerTransaction)

        mock_conn.commit.assert_called_once()
        mock_conn.rollback.assert_not_called()
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("pyodbc.connect")
    async def test_transaction_rolls_back_on_exception(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        adapter = SqlServerAdapter(self._CONN_STR)
        with pytest.raises(RuntimeError, match="fail"):
            async with adapter.transaction():
                raise RuntimeError("fail")

        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("pyodbc.connect")
    async def test_transaction_closes_connection_even_after_rollback_error(
        self, mock_connect
    ):
        mock_conn = MagicMock()
        mock_conn.rollback.side_effect = RuntimeError("rollback failed")
        mock_connect.return_value = mock_conn

        adapter = SqlServerAdapter(self._CONN_STR)
        with pytest.raises(RuntimeError):
            async with adapter.transaction():
                raise RuntimeError("original error")

        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_is_noop(self):
        adapter = SqlServerAdapter(self._CONN_STR)
        await adapter.disconnect()  # must not raise
