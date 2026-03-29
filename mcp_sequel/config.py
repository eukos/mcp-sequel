from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, ValidationError


class MySQLConfig(BaseModel):
    type: Literal["mysql", "mariadb"]
    host: str
    port: int = 3306
    database: str | None = None
    user: str
    password: str
    readonly: bool = True
    row_limit: int | None = 1000
    description: str | None = None


ConnectionConfig = Annotated[
    MySQLConfig,
    Field(discriminator="type"),
]


def config_dir() -> Path:
    return Path.home() / ".config" / "mcp-sequel"


def load_one(name: str) -> "ConnectionConfig | None":
    path = config_dir() / f"{name}.json"
    if not path.exists():
        return None
    from pydantic import TypeAdapter

    adapter = TypeAdapter(ConnectionConfig)
    return adapter.validate_json(path.read_text())


def load_all() -> list[tuple[str, ConnectionConfig]]:
    """Return [(name, config), ...] for all valid .json files in the config dir."""
    directory = config_dir()
    if not directory.exists():
        return []

    results = []
    for path in sorted(directory.glob("*.json")):
        name = path.stem
        try:
            from pydantic import TypeAdapter

            adapter = TypeAdapter(ConnectionConfig)
            config = adapter.validate_json(path.read_text())
            results.append((name, config))
        except ValidationError as e:
            # Skip invalid configs but don't crash the server
            import sys

            print(f"WARNING: skipping {path.name}: {e}", file=sys.stderr)

    return results
