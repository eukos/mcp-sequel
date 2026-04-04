# mcp-sequel

MCP server for Claude that connects to MySQL/MariaDB/SQLite databases.
Supports multiple connections, multiple databases, and readonly mode.

## Install

```bash
pip install -e .        # editable, for development
uvx mcp-sequel          # run directly without installing
```

## Claude registration

```bash
claude mcp add --transport stdio mcp-sequel -- uvx mcp-sequel
claude mcp add mcp-sequel -- uv run --directory /Users/eugenekosyakov/Documents/my/mcp-sequel mcp-sequel
```

## Configuration

One file per connection in `~/.config/mcp-sequel/`. The filename (without `.json`) becomes the connection name.

```bash
~/.config/mcp-sequel/
├── production.json
├── staging.json
└── local.json
```

Each file is one connection. Examples:

**MySQL / MariaDB**

```json
{
  "type": "mysql",
  "host": "db.example.com",
  "port": 3306,
  "user": "analyst",
  "password": "secret",
  "database": "myapp",
  "readonly": true,
  "row_limit": 1000,
  "description": "Production replica, analytics only"
}
```

| Field         | Required | Default | Description                                            |
|---------------|----------|---------|--------------------------------------------------------|
| `type`        | yes      | —       | `"mysql"` or `"mariadb"`                               |
| `host`        | yes      | —       | hostname or IP                                         |
| `user`        | yes      | —       | database user                                          |
| `password`    | yes      | —       | database password                                      |
| `port`        | no       | `3306`  | TCP port                                               |
| `database`    | no       | —       | default database; can be overridden per query          |
| `readonly`    | no       | `true`  | if true, only SELECT/SHOW/DESCRIBE/EXPLAIN are allowed |
| `row_limit`   | no       | `1000`  | max rows returned; `null` for no limit                 |
| `description` | no       | —       | human-readable label shown in `list_connections`       |

**SQLite**

```json
{
  "type": "sqlite",
  "path": "/data/analytics.db",
  "readonly": true,
  "row_limit": 1000,
  "description": "Local analytics database"
}
```

| Field         | Required | Default | Description                                                        |
|---------------|----------|---------|--------------------------------------------------------------------|
| `type`        | yes      | —       | `"sqlite"`                                                         |
| `path`        | yes      | —       | absolute path to the `.db` file                                    |
| `readonly`    | no       | `true`  | if true, opens connection with `?mode=ro` (OS-level enforcement)   |
| `row_limit`   | no       | `1000`  | max rows returned; `null` for no limit                             |
| `description` | no       | —       | human-readable label shown in `list_connections`                   |

Set permissions to owner-only:

```bash
chmod 600 ~/.config/mcp-sequel/*.json
```

## License

MIT
