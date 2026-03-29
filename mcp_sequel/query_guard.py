import sqlglot

from mcp_sequel.adapters.base import BaseAdapter


class ReadonlyViolationError(Exception):
    pass


def check_readonly(sql: str, adapter: BaseAdapter) -> None:
    stmts = sqlglot.parse(sql, dialect=adapter.sqlglot_dialect)
    if not stmts:
        raise ReadonlyViolationError("could not parse SQL")
    for stmt in stmts:
        stmt_type = type(stmt).__name__.upper()
        if stmt_type not in adapter.ALLOWED_STATEMENTS:
            raise ReadonlyViolationError(
                f"{stmt_type} statement is not allowed in readonly mode"
            )
