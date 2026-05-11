# mcp-sequel

MCP server for Claude that connects to MySQL/MariaDB/SQLite databases.
Supports multiple connections, multiple databases, and readonly mode.

## Install & Registration

Clone the repo, then register with Claude:

```bash
git clone https://github.com/eukos/mcp-sequel
claude mcp add mcp-sequel -- uv run --directory /path/to/mcp-sequel mcp-sequel
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
| `ssh_tunnel`  | no       | —       | SSH tunnel config (see below); routes the connection through a bastion host |

**MySQL via SSH tunnel**

Use `ssh_tunnel` when the database is only reachable through a bastion/jump host. `host` and `port` in the top-level config refer to the DB as seen **from the SSH server** (commonly `localhost`).

With a key file (most common):

```json
{
  "type": "mysql",
  "host": "localhost",
  "port": 3306,
  "user": "reader",
  "password": "secret",
  "database": "myapp",
  "ssh_tunnel": {
    "host": "bastion.example.com",
    "user": "ubuntu",
    "key_file": "~/.ssh/id_rsa"
  }
}
```

With an SSH password:

```json
{
  "type": "mysql",
  "host": "localhost",
  "port": 3306,
  "user": "reader",
  "password": "secret",
  "ssh_tunnel": {
    "host": "bastion.example.com",
    "user": "ubuntu",
    "password": "sshpass"
  }
}
```

| Field      | Required | Default | Description                             |
|------------|----------|---------|-----------------------------------------|
| `host`     | yes      | —       | SSH server hostname or IP               |
| `user`     | yes      | —       | SSH username                            |
| `key_file` | no\*     | —       | path to private key file (`~` expanded) |
| `password` | no\*     | —       | SSH password (if not using key file)    |
| `port`     | no       | `22`    | SSH server port                         |

\* at least one of `key_file` or `password` should be provided.

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
