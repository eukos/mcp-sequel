from mcp_sequel.adapters.mysql import MySQLAdapter

ADAPTERS: dict[str, type] = {
    "mysql": MySQLAdapter,
    "mariadb": MySQLAdapter,
}
