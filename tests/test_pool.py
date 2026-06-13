from unittest.mock import MagicMock, patch

import pytest

import mcp_sequel.pool as pool_module
from mcp_sequel.pool import close_all, get_connection


class _Config:
    type = "mysql"


def _make_adapter_class(pool_key_fn=None):
    """Return a mock adapter class with controllable make_pool_key."""
    adapter_instance = MagicMock()
    adapter_instance.ping.return_value = True

    adapter_class = MagicMock()
    adapter_class.return_value = adapter_instance
    adapter_class.make_pool_key = pool_key_fn or (lambda name, db, cfg: name)

    return adapter_class, adapter_instance


@pytest.fixture(autouse=True)
def clear_pool():
    pool_module._pool.clear()
    yield
    pool_module._pool.clear()


def test_unknown_connection_raises():
    with patch("mcp_sequel.pool.load_one", return_value=None):
        with pytest.raises(ValueError, match="not found"):
            get_connection("missing")


def test_creates_connection_and_caches():
    cfg = _Config()
    adapter_class, adapter_instance = _make_adapter_class()

    with (
        patch("mcp_sequel.pool.load_one", return_value=cfg),
        patch.dict("mcp_sequel.pool.ADAPTERS", {"mysql": adapter_class}, clear=False),
    ):
        result1 = get_connection("myconn")
        result2 = get_connection("myconn")

    # adapter constructed only once
    assert adapter_class.call_count == 1
    adapter_instance.connect.assert_called_once()
    # both calls return same objects
    assert result1 == result2


def test_ping_called_on_cache_hit():
    cfg = _Config()
    adapter_class, adapter_instance = _make_adapter_class()

    with (
        patch("mcp_sequel.pool.load_one", return_value=cfg),
        patch.dict("mcp_sequel.pool.ADAPTERS", {"mysql": adapter_class}, clear=False),
    ):
        get_connection("myconn")
        get_connection("myconn")

    adapter_instance.ping.assert_called_once()


def test_database_passed_to_adapter_constructor():
    cfg = _Config()
    adapter_class, _ = _make_adapter_class()

    with (
        patch("mcp_sequel.pool.load_one", return_value=cfg),
        patch.dict("mcp_sequel.pool.ADAPTERS", {"mysql": adapter_class}, clear=False),
    ):
        get_connection("myconn", database="shop")

    adapter_class.assert_called_once_with(cfg, "shop")


def test_default_pool_key_is_conn_name_regardless_of_database():
    cfg = _Config()
    adapter_class, adapter_instance = _make_adapter_class()

    with (
        patch("mcp_sequel.pool.load_one", return_value=cfg),
        patch.dict("mcp_sequel.pool.ADAPTERS", {"mysql": adapter_class}, clear=False),
    ):
        get_connection("myconn", database="db1")
        get_connection("myconn", database="db2")

    # default make_pool_key returns conn_name, so both hits the same pool slot
    assert adapter_class.call_count == 1


def test_custom_pool_key_creates_separate_connections():
    cfg = _Config()
    adapter_class, _ = _make_adapter_class(
        pool_key_fn=lambda name, db, cfg: f"{name}__{db}" if db else name
    )

    with (
        patch("mcp_sequel.pool.load_one", return_value=cfg),
        patch.dict("mcp_sequel.pool.ADAPTERS", {"mysql": adapter_class}, clear=False),
    ):
        get_connection("myconn", database="shop")
        get_connection("myconn", database="blog")

    # different pool keys → two separate connections
    assert adapter_class.call_count == 2


def test_close_all_closes_and_clears():
    cfg = _Config()
    adapter_class, adapter_instance = _make_adapter_class()

    with (
        patch("mcp_sequel.pool.load_one", return_value=cfg),
        patch.dict("mcp_sequel.pool.ADAPTERS", {"mysql": adapter_class}, clear=False),
    ):
        get_connection("myconn")

    close_all()

    adapter_instance.close.assert_called_once()
    assert pool_module._pool == {}
