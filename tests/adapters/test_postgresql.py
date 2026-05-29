import ipaddress
import uuid
from unittest.mock import MagicMock, patch

import pytest

from mcp_sequel.adapters.postgres import PostgreSQLAdapter


class _Config:
    type = "postgresql"
    host = "localhost"
    port = 5432
    user = "dev"
    password = "devpass"
    database = "mydb"
    readonly = False
    ssh_tunnel = None


class _ConfigNoDb:
    type = "postgresql"
    host = "localhost"
    port = 5432
    user = "dev"
    password = "devpass"
    database = None
    readonly = False
    ssh_tunnel = None


class _ConfigReadonly:
    type = "postgresql"
    host = "localhost"
    port = 5432
    user = "dev"
    password = "devpass"
    database = "mydb"
    readonly = True
    ssh_tunnel = None


class _ConfigWithTunnel:
    type = "postgresql"
    host = "db.internal"
    port = 5432
    user = "dev"
    password = "devpass"
    database = "mydb"
    readonly = False
    ssh_tunnel = MagicMock()


def _make_conn(columns=None, rows=None):
    """Return (mock_conn, mock_cursor) with description and fetchall pre-set."""
    cursor = MagicMock()
    cursor.description = [((col,)) for col in (columns or [])] or None
    cursor.fetchall.return_value = rows or []
    conn = MagicMock()
    conn.execute.return_value = cursor
    return conn, cursor


# --- make_pool_key ---


def test_make_pool_key_uses_passed_database():
    assert PostgreSQLAdapter.make_pool_key("conn", "shop", _Config()) == "conn__shop"


def test_make_pool_key_uses_config_database_when_none_passed():
    assert PostgreSQLAdapter.make_pool_key("conn", None, _Config()) == "conn__mydb"


def test_make_pool_key_raises_without_database():
    with pytest.raises(RuntimeError, match="requires a database"):
        PostgreSQLAdapter.make_pool_key("conn", None, _ConfigNoDb())


# --- _database resolution in __init__ ---


def test_database_resolution_passed_wins_over_config():
    adapter = PostgreSQLAdapter(_Config(), database="shop")
    assert adapter._database == "shop"


def test_database_resolution_uses_config_database():
    adapter = PostgreSQLAdapter(_Config())
    assert adapter._database == "mydb"


def test_database_resolution_raises_without_database():
    with pytest.raises(RuntimeError, match="requires a database"):
        PostgreSQLAdapter(_ConfigNoDb())


# --- connect ---


def test_connect_without_tunnel():
    cfg = _Config()
    adapter = PostgreSQLAdapter(cfg)
    mock_conn = MagicMock()

    with patch("mcp_sequel.adapters.postgres.psycopg") as mock_psycopg:
        mock_psycopg.connect.return_value = mock_conn
        conn = adapter.connect()

    mock_psycopg.connect.assert_called_once_with(
        host="localhost",
        port=5432,
        user="dev",
        password="devpass",
        dbname="mydb",
        autocommit=True,
    )
    mock_conn.execute.assert_not_called()
    assert conn is mock_conn


def test_connect_readonly_sets_transaction_readonly():
    cfg = _ConfigReadonly()
    adapter = PostgreSQLAdapter(cfg)
    mock_conn = MagicMock()

    with patch("mcp_sequel.adapters.postgres.psycopg") as mock_psycopg:
        mock_psycopg.connect.return_value = mock_conn
        adapter.connect()

    mock_conn.execute.assert_called_once_with("SET default_transaction_read_only = on")


def test_connect_with_tunnel():
    cfg = _ConfigWithTunnel()
    adapter = PostgreSQLAdapter(cfg)
    mock_conn = MagicMock()
    mock_tunnel = MagicMock()
    mock_tunnel.local_bind_port = 54321

    with (
        patch("mcp_sequel.adapters.postgres.psycopg") as mock_psycopg,
        patch(
            "mcp_sequel.adapters.postgres.open_tunnel", return_value=mock_tunnel
        ) as mock_open,
    ):
        mock_psycopg.connect.return_value = mock_conn
        adapter.connect()

    mock_open.assert_called_once_with(cfg.ssh_tunnel, "db.internal", 5432)
    mock_psycopg.connect.assert_called_once_with(
        host="127.0.0.1",
        port=54321,
        user="dev",
        password="devpass",
        dbname="mydb",
        autocommit=True,
    )
    assert adapter._tunnel is mock_tunnel


# --- ping ---


def test_ping_executes_select_1():
    adapter = PostgreSQLAdapter(_Config())
    conn = MagicMock()
    assert adapter.ping(conn) is True
    conn.execute.assert_called_once_with("SELECT 1")


# --- execute ---


def test_execute_columns_and_rows():
    adapter = PostgreSQLAdapter(_Config())
    conn, _ = _make_conn(columns=["id", "name"], rows=[(1, "alice"), (2, "bob")])

    result = adapter.execute(conn, "SELECT id, name FROM users", None)

    assert result.columns == ["id", "name"]
    assert result.rows == [[1, "alice"], [2, "bob"]]
    assert result.row_count == 2


def test_execute_empty_result():
    adapter = PostgreSQLAdapter(_Config())
    conn = MagicMock()
    cursor = MagicMock()
    cursor.description = None
    cursor.fetchall.return_value = []
    conn.execute.return_value = cursor

    result = adapter.execute(conn, "SELECT 1 WHERE false", None)

    assert result.columns == []
    assert result.rows == []


def test_execute_database_mismatch_raises():
    adapter = PostgreSQLAdapter(_Config())  # _database = "mydb"
    conn, _ = _make_conn()

    with pytest.raises(RuntimeError, match="does not support switching"):
        adapter.execute(conn, "SELECT 1", "other_db")


def test_execute_same_database_ok():
    adapter = PostgreSQLAdapter(_Config())  # _database = "mydb"
    conn, _ = _make_conn(columns=["x"], rows=[(1,)])

    result = adapter.execute(conn, "SELECT 1", "mydb")
    assert result.row_count == 1


def test_execute_none_database_ok():
    adapter = PostgreSQLAdapter(_Config())
    conn, _ = _make_conn(columns=["x"], rows=[(42,)])

    result = adapter.execute(conn, "SELECT 42", None)
    assert result.rows == [[42]]


def test_execute_serializes_postgresql_types():
    uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    ip = ipaddress.IPv4Address("192.168.1.1")

    adapter = PostgreSQLAdapter(_Config())
    conn, _ = _make_conn(columns=["uid", "ip"], rows=[(uid, ip)])

    result = adapter.execute(conn, "SELECT uid, ip FROM type_zoo", None)

    assert result.rows == [["12345678-1234-5678-1234-567812345678", "192.168.1.1"]]


# --- close ---


def test_close_closes_connection():
    adapter = PostgreSQLAdapter(_Config())
    conn = MagicMock()
    adapter.close(conn)
    conn.close.assert_called_once()


def test_close_stops_tunnel():
    adapter = PostgreSQLAdapter(_ConfigWithTunnel())
    tunnel = MagicMock()
    adapter._tunnel = tunnel
    conn = MagicMock()

    with patch("mcp_sequel.adapters.postgres.close_tunnel") as mock_close:
        adapter.close(conn)

    mock_close.assert_called_once_with(tunnel)
    assert adapter._tunnel is None


def test_close_without_tunnel_does_not_call_close_tunnel():
    adapter = PostgreSQLAdapter(_Config())
    conn = MagicMock()

    with patch("mcp_sequel.adapters.postgres.close_tunnel") as mock_close:
        adapter.close(conn)

    mock_close.assert_not_called()
