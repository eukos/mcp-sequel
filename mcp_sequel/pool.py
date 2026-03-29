from typing import Any

from mcp_sequel.adapters import ADAPTERS
from mcp_sequel.adapters.base import BaseAdapter
from mcp_sequel.config import ConnectionConfig, load_one

_pool: dict[str, tuple[ConnectionConfig, BaseAdapter, Any]] = {}


def get_connection(conn_name: str) -> tuple[ConnectionConfig, BaseAdapter, Any]:
    if conn_name in _pool:
        cfg, adapter, conn = _pool[conn_name]
        adapter.ping(conn)
        return cfg, adapter, conn

    cfg = load_one(conn_name)
    if cfg is None:
        raise ValueError(f"Connection '{conn_name}' not found")

    adapter_class = ADAPTERS[cfg.type]
    adapter = adapter_class(cfg)
    conn = adapter.connect()
    _pool[conn_name] = (cfg, adapter, conn)
    return cfg, adapter, conn


def close_all() -> None:
    for cfg, adapter, conn in _pool.values():
        try:
            adapter.close(conn)
        except Exception:
            pass
    _pool.clear()
