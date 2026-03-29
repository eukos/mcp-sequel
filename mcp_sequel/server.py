import json

import sqlglot
from mcp.server.fastmcp import FastMCP

from mcp_sequel.config import load_all
from mcp_sequel.pool import get_connection
from mcp_sequel.query_guard import ReadonlyViolationError, check_readonly

mcp = FastMCP("mcp-sequel")


def _is_select_without_limit(sql: str, dialect: str) -> bool:
    stmts = sqlglot.parse(sql, dialect=dialect)
    if not stmts or len(stmts) != 1:
        return False
    stmt = stmts[0]
    return isinstance(stmt, sqlglot.exp.Select) and stmt.args.get("limit") is None


@mcp.tool()
def list_connections() -> str:
    """List all configured database connections."""
    try:
        connections = load_all()
    except Exception as e:
        return f"ERROR: failed to load configs: {e}"

    if not connections:
        from mcp_sequel.config import config_dir

        return f"No connections configured. Add .json files to: {config_dir()}"

    blocks = []
    for name, cfg in connections:
        host = cfg.host if cfg.port == 3306 else f"{cfg.host}:{cfg.port}"
        location = f"{cfg.user}@{host}"
        if cfg.database:
            location += f"/{cfg.database}"
        readonly = "yes" if cfg.readonly else "no"

        header = f"{name} ({location}) [{cfg.type}], readonly: {readonly}"
        if cfg.description:
            blocks.append(f"{header}\n  {cfg.description}")
        else:
            blocks.append(header)

    return "\n\n".join(blocks)


@mcp.tool()
def query(connection: str, sql: str, database: str | None = None) -> str:
    """Execute a SQL query on a database connection. Returns JSON with columns, rows, row_count, limit_applied."""
    try:
        cfg, adapter, conn = get_connection(connection)

        if cfg.readonly:
            check_readonly(sql, adapter)

        actual_sql = sql
        limit_applied = None
        if cfg.row_limit is not None and _is_select_without_limit(
            sql, adapter.sqlglot_dialect
        ):
            actual_sql = sql.rstrip().rstrip(";") + f" LIMIT {cfg.row_limit}"
            limit_applied = cfg.row_limit

        result = adapter.execute(conn, actual_sql, database)
        result.limit_applied = limit_applied

        return json.dumps(
            {
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
                "limit_applied": result.limit_applied,
            }
        )
    except ReadonlyViolationError as e:
        return f"ERROR: readonly violation: {e}"
    except Exception as e:
        return f"ERROR: {e}"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
