import datetime
import decimal
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


def _serialize(value: Any) -> Any:
    if isinstance(value, (datetime.date, datetime.datetime, datetime.timedelta)):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


class ReadonlyViolationError(Exception):
    pass


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list]
    row_count: int
    limit_applied: int | None


class BaseAdapter(ABC):
    ALLOWED_STATEMENTS: frozenset[str] = frozenset()
    sqlglot_dialect: str = ""

    def __init__(self, config: Any) -> None:
        self.config = config

    def guard_readonly(self, sql: str) -> None:
        # No-op by default. Two strategies exist:
        # - Connection-level enforcement (SQLite: file URI with mode=ro) — leave as no-op
        # - Statement-level enforcement (MySQL: parse SQL, reject non-SELECT) — override this method
        pass

    @abstractmethod
    def connect(self) -> Any: ...

    @abstractmethod
    def ping(self, conn: Any) -> bool: ...

    @abstractmethod
    def execute(self, conn: Any, sql: str, database: str | None) -> QueryResult: ...

    @abstractmethod
    def close(self, conn: Any) -> None: ...

