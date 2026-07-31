from unittest.mock import MagicMock, patch

import mcp_sequel.server as server


class _Config:
    readonly = False
    row_limit = None


def _make_adapter():
    adapter = MagicMock()
    adapter.sqlglot_dialect = "mysql"
    adapter.execute.return_value = MagicMock(
        columns=["x"], rows=[[1]], row_count=1, limit_applied=None
    )
    return adapter


def test_query_forwards_explicit_timeout():
    cfg = _Config()
    adapter = _make_adapter()
    conn = MagicMock()

    with patch("mcp_sequel.server.get_connection", return_value=(cfg, adapter, conn)):
        server.query("myconn", "SELECT 1", timeout=5)

    adapter.execute.assert_called_once_with(conn, "SELECT 1", None, 5)


def test_query_forwards_default_timeout():
    cfg = _Config()
    adapter = _make_adapter()
    conn = MagicMock()

    with patch("mcp_sequel.server.get_connection", return_value=(cfg, adapter, conn)):
        server.query("myconn", "SELECT 1")

    adapter.execute.assert_called_once_with(conn, "SELECT 1", None, 60)
