import sqlite3
from typing import Any

from mcp_sequel.adapters.base import BaseAdapter, QueryResult, _serialize


class SQLiteAdapter(BaseAdapter):
    sqlglot_dialect = "sqlite"

    def connect(self) -> sqlite3.Connection:
        path = self.config.path
        if self.config.readonly:
            uri = f"file:{path}?mode=ro"
            return sqlite3.connect(uri, uri=True)
        return sqlite3.connect(path)

    def ping(self, conn: sqlite3.Connection) -> bool:
        conn.execute("SELECT 1")
        return True

    def execute(
        self, conn: sqlite3.Connection, sql: str, database: str | None
    ) -> QueryResult:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        raw_rows = cursor.fetchall() or []
        rows = [[_serialize(v) for v in row] for row in raw_rows]
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            limit_applied=None,
        )

    def close(self, conn: sqlite3.Connection) -> None:
        conn.close()
