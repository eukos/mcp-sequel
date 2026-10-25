import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

import mcp_sequel.pool as pool_module
import mcp_sequel.server as server
from mcp_sequel.config import SQLiteConfig

# MCP SDK v2 runs sync tools in worker threads, so query() must tolerate
# concurrent calls against the shared connection pool.


@pytest.fixture(autouse=True)
def clear_pool():
    pool_module._pool.clear()
    yield
    pool_module._pool.clear()


def test_concurrent_queries_share_pooled_sqlite_connection(tmp_path):
    db = tmp_path / "t.db"
    with sqlite3.connect(db) as c:
        c.execute("create table x(a)")
        c.execute("insert into x values (1)")
    cfg = SQLiteConfig(type="sqlite", path=str(db), readonly=False)

    with patch("mcp_sequel.pool.load_one", return_value=cfg):
        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(
                ex.map(lambda _: server.query("lite", "select * from x"), range(40))
            )

    assert all(not r.startswith("ERROR") for r in results), results
    assert all(json.loads(r)["rows"] == [[1]] for r in results)


def test_queries_never_execute_concurrently():
    state = {"active": 0, "max_active": 0}
    guard = threading.Lock()

    def slow_execute(*args, **kwargs):
        with guard:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        time.sleep(0.02)
        with guard:
            state["active"] -= 1
        return MagicMock(columns=["x"], rows=[[1]], row_count=1, limit_applied=None)

    adapter = MagicMock()
    adapter.sqlglot_dialect = "mysql"
    adapter.execute.side_effect = slow_execute
    cfg = MagicMock(readonly=False, row_limit=None)

    with patch("mcp_sequel.server.get_connection", return_value=(cfg, adapter, None)):
        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(lambda _: server.query("c", "select 1"), range(16)))

    assert all(not r.startswith("ERROR") for r in results), results
    assert state["max_active"] == 1
