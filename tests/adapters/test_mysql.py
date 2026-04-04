import datetime
from unittest.mock import MagicMock, patch

import pytest

from mcp_sequel.adapters.base import ReadonlyViolationError
from mcp_sequel.adapters.mysql import MySQLAdapter


class _Config:
    readonly = True
    row_limit = None
    type = "mysql"


@pytest.fixture
def adapter():
    return MySQLAdapter(_Config())


# --- guard_readonly ---


def test_guard_readonly_blocks_write(adapter):
    with pytest.raises(ReadonlyViolationError, match="INSERT"):
        adapter.guard_readonly("INSERT INTO t VALUES (1)")

    with pytest.raises(ReadonlyViolationError, match="DELETE"):
        adapter.guard_readonly("DELETE FROM t")

    with pytest.raises(ReadonlyViolationError, match="DROP"):
        adapter.guard_readonly("DROP TABLE t")


def test_guard_readonly_allows_reads(adapter):
    adapter.guard_readonly("SELECT 1")
    adapter.guard_readonly("SHOW TABLES")
    adapter.guard_readonly("DESCRIBE users")
    adapter.guard_readonly("EXPLAIN SELECT * FROM t")


# --- execute ---


def _make_conn(description, rows):
    cursor = MagicMock()
    cursor.description = description
    cursor.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def test_execute_normal_select(adapter):
    description = [("id",), ("name",)]
    conn, cursor = _make_conn(description, [(1, "alice"), (2, "bob")])

    result = adapter.execute(conn, "SELECT id, name FROM t", None)

    assert result.columns == ["id", "name"]
    assert result.rows == [[1, "alice"], [2, "bob"]]
    assert result.row_count == 2
    assert result.limit_applied is None


def test_execute_with_database_switch(adapter):
    description = [("x",)]
    conn, cursor = _make_conn(description, [(1,)])

    adapter.execute(conn, "SELECT x FROM t", "mydb")

    calls = [call.args[0] for call in cursor.execute.call_args_list]
    assert calls[0] == "USE `mydb`"
    assert calls[1] == "SELECT x FROM t"


def test_execute_serializes_values(adapter):
    description = [("ts",), ("data",)]
    dt = datetime.datetime(2025, 1, 1, 0, 0, 0)
    conn, cursor = _make_conn(description, [(dt, b"\x01\x02")])

    result = adapter.execute(conn, "SELECT ts, data FROM t", None)

    assert result.rows == [["2025-01-01 00:00:00", "0102"]]


def test_execute_empty_result(adapter):
    conn, _ = _make_conn(None, [])

    result = adapter.execute(conn, "SELECT * FROM t", None)

    assert result.columns == []
    assert result.rows == []
    assert result.row_count == 0


# --- tunnel integration ---


class _FullConfig:
    """Config with all fields needed by connect()."""

    readonly = True
    row_limit = None
    type = "mysql"
    host = "db.internal"
    port = 3306
    user = "root"
    password = "secret"
    database = None
    ssh_tunnel = None


class _FullConfigWithTunnel(_FullConfig):
    ssh_tunnel = MagicMock()  # truthy ssh_tunnel object


def test_connect_without_tunnel_uses_config_host_port():
    adapter = MySQLAdapter(_FullConfig())
    with patch("mcp_sequel.adapters.mysql.mysql.connector.connect") as mock_connect:
        mock_connect.return_value = MagicMock()
        adapter.connect()

    mock_connect.assert_called_once_with(
        host="db.internal",
        port=3306,
        user="root",
        password="secret",
        database=None,
    )
    assert adapter._tunnel is None


def test_connect_with_tunnel_uses_local_bind_port():
    adapter = MySQLAdapter(_FullConfigWithTunnel())
    mock_tunnel = MagicMock()
    mock_tunnel.local_bind_port = 55555

    with (
        patch(
            "mcp_sequel.adapters.mysql.open_tunnel", return_value=mock_tunnel
        ) as mock_open,
        patch("mcp_sequel.adapters.mysql.mysql.connector.connect") as mock_connect,
    ):
        mock_connect.return_value = MagicMock()
        adapter.connect()

    mock_open.assert_called_once_with(
        _FullConfigWithTunnel.ssh_tunnel, "db.internal", 3306
    )
    mock_connect.assert_called_once_with(
        host="127.0.0.1",
        port=55555,
        user="root",
        password="secret",
        database=None,
    )
    assert adapter._tunnel is mock_tunnel


def test_close_stops_tunnel():
    adapter = MySQLAdapter(_FullConfigWithTunnel())
    mock_tunnel = MagicMock()
    adapter._tunnel = mock_tunnel
    mock_conn = MagicMock()

    with patch("mcp_sequel.adapters.mysql.close_tunnel") as mock_close:
        adapter.close(mock_conn)

    mock_conn.close.assert_called_once()
    mock_close.assert_called_once_with(mock_tunnel)
    assert adapter._tunnel is None


def test_close_without_tunnel_does_not_call_close_tunnel():
    adapter = MySQLAdapter(_FullConfig())
    adapter._tunnel = None
    mock_conn = MagicMock()

    with patch("mcp_sequel.adapters.mysql.close_tunnel") as mock_close:
        adapter.close(mock_conn)

    mock_conn.close.assert_called_once()
    mock_close.assert_not_called()
