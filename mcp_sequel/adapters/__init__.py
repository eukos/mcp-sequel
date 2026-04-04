from mcp_sequel.adapters.mysql import MySQLAdapter
from mcp_sequel.adapters.sqlite import SQLiteAdapter

ADAPTERS: dict[str, type] = {
    "mysql": MySQLAdapter,
    "mariadb": MySQLAdapter,
    "sqlite": SQLiteAdapter,
}
