from typing import Any

import mysql.connector
import sqlglot

from mcp_sequel.adapters.base import (
    BaseAdapter,
    QueryResult,
    ReadonlyViolationError,
    _serialize,
)
from mcp_sequel.tunnel import close_tunnel, open_tunnel


class MySQLAdapter(BaseAdapter):
    ALLOWED_STATEMENTS = frozenset({"SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "USE"})

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self.sqlglot_dialect = config.type  # "mysql" or "mariadb"
        self._tunnel: Any = None

    def guard_readonly(self, sql: str) -> None:
        stmts = sqlglot.parse(sql, dialect=self.sqlglot_dialect)
        if not stmts:
            raise ReadonlyViolationError("could not parse SQL")
        for stmt in stmts:
            stmt_type = type(stmt).__name__.upper()
            if stmt_type not in self.ALLOWED_STATEMENTS:
                raise ReadonlyViolationError(
                    f"{stmt_type} statement is not allowed in readonly mode"
                )

    def connect(self) -> Any:
        if self.config.ssh_tunnel:
            self._tunnel = open_tunnel(
                self.config.ssh_tunnel,
                self.config.host,
                self.config.port,
            )
            host = "127.0.0.1"
            port = self._tunnel.local_bind_port
        else:
            self._tunnel = None
            host = self.config.host
            port = self.config.port

        return mysql.connector.connect(
            host=host,
            port=port,
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
        if self._tunnel is not None:
            close_tunnel(self._tunnel)
            self._tunnel = None
