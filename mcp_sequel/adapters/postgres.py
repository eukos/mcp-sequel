from typing import Any

import psycopg

from mcp_sequel.adapters.base import BaseAdapter, QueryResult, _serialize
from mcp_sequel.tunnel import close_tunnel, open_tunnel


class PostgreSQLAdapter(BaseAdapter):
    sqlglot_dialect = "postgres"

    def __init__(self, config: Any, database: str | None = None) -> None:
        super().__init__(config, database)
        self._database = database or config.database
        if not self._database:
            raise RuntimeError(
                "PostgreSQL requires a database. Pass one via the 'database' parameter or set it in the connection config."
            )
        self._tunnel: Any = None

    @classmethod
    def make_pool_key(cls, conn_name: str, database: str | None, cfg: Any) -> str:
        effective = database or cfg.database
        if not effective:
            raise RuntimeError(
                "PostgreSQL requires a database. Pass one via the 'database' parameter or set it in the connection config."
            )
        return f"{conn_name}__{effective}"

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

        conn = psycopg.connect(
            host=host,
            port=port,
            user=self.config.user,
            password=self.config.password,
            dbname=self._database,
            autocommit=True,
        )
        if self.config.readonly:
            conn.execute("SET default_transaction_read_only = on")
        return conn

    def ping(self, conn: Any) -> bool:
        conn.execute("SELECT 1")
        return True

    def execute(
        self, conn: Any, sql: str, database: str | None, timeout: int = 60
    ) -> QueryResult:
        if database is not None and database != self._database:
            raise RuntimeError(
                f"PostgreSQL does not support switching databases mid-connection "
                f"(connected to '{self._database}', requested '{database}'). "
                f"Use a separate connection config for each database."
            )
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

    def close(self, conn: Any) -> None:
        conn.close()
        if self._tunnel is not None:
            close_tunnel(self._tunnel)
            self._tunnel = None
