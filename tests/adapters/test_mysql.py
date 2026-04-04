import datetime
from unittest.mock import MagicMock

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
