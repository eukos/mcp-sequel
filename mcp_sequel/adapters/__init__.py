from mcp_sequel.adapters.mysql import MySQLAdapter
from mcp_sequel.adapters.postgres import PostgreSQLAdapter
from mcp_sequel.adapters.sqlite import SQLiteAdapter

ADAPTERS: dict[str, type] = {
    "mariadb": MySQLAdapter,
    "mysql": MySQLAdapter,
    "postgresql": PostgreSQLAdapter,
    "sqlite": SQLiteAdapter,
}
