import datetime
import os
import sqlite3
import tempfile

import pytest
from mcp_sequel.adapters.sqlite import SQLiteAdapter


class _Config:
    readonly = False
    row_limit = None
    path = ":memory:"


def _adapter(path=":memory:", readonly=False):
    cfg = _Config()
    cfg.path = path
    cfg.readonly = readonly
    return SQLiteAdapter(cfg)


# --- guard_readonly (no-op: SQLite enforces readonly at connection level) ---


def test_guard_readonly_is_noop():
    adapter = _adapter()
    adapter.guard_readonly("INSERT INTO t VALUES (1)")
    adapter.guard_readonly("DELETE FROM t")
    adapter.guard_readonly("DROP TABLE t")


def test_readonly_write_raises_operational_error():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        conn_rw = sqlite3.connect(path)
        conn_rw.execute("CREATE TABLE t (id INTEGER)")
        conn_rw.close()

        adapter = _adapter(path=path, readonly=True)
        conn = adapter.connect()
        try:
            with pytest.raises(sqlite3.OperationalError):
                adapter.execute(conn, "INSERT INTO t VALUES (1)", None)
        finally:
            adapter.close(conn)
    finally:
        os.unlink(path)


# --- connect ---


def test_connect_readwrite():
    adapter = _adapter(path=":memory:", readonly=False)
    conn = adapter.connect()
    try:
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
    finally:
        adapter.close(conn)


def test_connect_readonly_blocks_write():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        conn_rw = sqlite3.connect(path)
        conn_rw.execute("CREATE TABLE t (id INTEGER)")
        conn_rw.close()

        adapter = _adapter(path=path, readonly=True)
        conn = adapter.connect()
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("INSERT INTO t VALUES (1)")
        finally:
            adapter.close(conn)
    finally:
        os.unlink(path)


# --- ping ---


def test_ping_returns_true():
    adapter = _adapter()
    conn = adapter.connect()
    try:
        assert adapter.ping(conn) is True
    finally:
        adapter.close(conn)


# --- execute ---


@pytest.fixture
def mem_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO t VALUES (1, 'alice')")
    conn.execute("INSERT INTO t VALUES (2, 'bob')")
    conn.commit()
    yield conn
    conn.close()


def test_execute_columns_and_rows(mem_conn):
    adapter = _adapter()
    result = adapter.execute(mem_conn, "SELECT id, name FROM t ORDER BY id", None)

    assert result.columns == ["id", "name"]
    assert result.rows == [[1, "alice"], [2, "bob"]]
    assert result.row_count == 2
    assert result.limit_applied is None


def test_execute_empty_result(mem_conn):
    adapter = _adapter()
    result = adapter.execute(mem_conn, "SELECT * FROM t WHERE id = 999", None)

    assert result.columns == ["id", "name"]
    assert result.rows == []
    assert result.row_count == 0


def test_execute_serializes_values():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (data BLOB)")
    conn.execute("INSERT INTO t VALUES (?)", (b"\x01\x02",))
    conn.commit()

    adapter = _adapter()
    result = adapter.execute(conn, "SELECT data FROM t", None)
    conn.close()

    assert result.rows == [["0102"]]


def test_execute_ignores_database_param(mem_conn):
    adapter = _adapter()
    result = adapter.execute(mem_conn, "SELECT id FROM t ORDER BY id", "ignored_db")

    assert result.row_count == 2
