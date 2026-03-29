from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


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

    @abstractmethod
    def connect(self) -> Any: ...

    @abstractmethod
    def ping(self, conn: Any) -> bool: ...

    @abstractmethod
    def execute(self, conn: Any, sql: str, database: str | None) -> QueryResult: ...

    @abstractmethod
    def close(self, conn: Any) -> None: ...
