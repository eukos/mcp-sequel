import datetime
import decimal
from typing import Any

import mysql.connector

from mcp_sequel.adapters.base import BaseAdapter, QueryResult


def _serialize(value: Any) -> Any:
    if isinstance(value, (datetime.date, datetime.datetime, datetime.timedelta)):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


class MySQLAdapter(BaseAdapter):
    ALLOWED_STATEMENTS = frozenset({"SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "USE"})

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self.sqlglot_dialect = config.type  # "mysql" or "mariadb"

    def connect(self) -> Any:
        return mysql.connector.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database or None,
        )

    def ping(self, conn: Any) -> bool:
        conn.ping(reconnect=True)
        return True

    def execute(self, conn: Any, sql: str, database: str | None) -> QueryResult:
        cursor = conn.cursor()
        try:
            if database is not None:
                cursor.execute(f"USE `{database}`")
            cursor.execute(sql)
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            raw_rows = cursor.fetchall() or []
            rows = [[_serialize(v) for v in row] for row in raw_rows]
            return QueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                limit_applied=None,
            )
        finally:
            cursor.close()

    def close(self, conn: Any) -> None:
        conn.close()
