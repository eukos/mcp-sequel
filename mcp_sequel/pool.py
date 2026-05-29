from typing import Any

from mcp_sequel.adapters import ADAPTERS
from mcp_sequel.adapters.base import BaseAdapter
from mcp_sequel.config import ConnectionConfig, load_one

_pool: dict[str, tuple[ConnectionConfig, BaseAdapter, Any]] = {}


def get_connection(
    conn_name: str, database: str | None = None
) -> tuple[ConnectionConfig, BaseAdapter, Any]:
    cfg = load_one(conn_name)
    if cfg is None:
        raise ValueError(f"Connection '{conn_name}' not found")

    adapter_class = ADAPTERS[cfg.type]
    pool_key = adapter_class.make_pool_key(conn_name, database, cfg)

    if pool_key in _pool:
        _, adapter, conn = _pool[pool_key]
        adapter.ping(conn)
        return cfg, adapter, conn

    adapter = adapter_class(cfg, database)
    conn = adapter.connect()
    _pool[pool_key] = (cfg, adapter, conn)
    return cfg, adapter, conn


def close_all() -> None:
    for cfg, adapter, conn in _pool.values():
        try:
            adapter.close(conn)
        except Exception:
            pass
    _pool.clear()
