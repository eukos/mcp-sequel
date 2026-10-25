# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.3.0] - 2026-10-25

### Changed
- Migrated to the MCP Python SDK v2 (`mcp>=2,<3`): `FastMCP` replaced by `MCPServer` (#31).

### Fixed
- Queries are serialized and SQLite connections can be used across threads, because SDK v2 runs synchronous tools in worker threads (previously a shared pooled connection could fail with "SQLite objects created in a thread can only be used in that same thread" on concurrent calls).

## [0.2.2] - 2026-07-31

### Fixed
- MySQL queries no longer hang forever if the network connection drops mid-query; added a per-query timeout, default 60s (#29). PostgreSQL, SQLite, and SSH-tunnel connections are not yet covered.
- Pinned `mcp` SDK to `>=1.28,<2`, fixing `uvx mcp-sequel` crashing with `ModuleNotFoundError: mcp.server.fastmcp` (an unbounded dependency resolve was pulling in the incompatible `mcp` 2.0 SDK).

### Security
- Upgraded `mcp` SDK to `>=1.28.1`, resolving 3 high-severity vulnerabilities: unauthorized task cancellation, missing HTTP transport principal verification, and missing WebSocket Host/Origin validation (#30).

## [0.2.1] - 2026-06-29

### Security
- Upgraded vulnerable transitive dependencies (#27).

## [0.2.0] - 2026-06-12

### Added
- PostgreSQL adapter with per-database connection pooling (#4).

### Changed
- Replaced the `sshtunnel` dependency with direct SSH port forwarding via paramiko (#25).

## [0.1.2] - 2026-05-27

### Added
- `get_version` MCP tool exposing the installed mcp-sequel version.
- Pre-merge CI check blocking RC versions from merging to `main`.
- CI requires tests to pass before publishing to PyPI.

### Changed
- Swapped `mysql-connector-python` for PyMySQL, dropping the explicit `paramiko` dependency (#17).

### Fixed
- Re-added the `paramiko<3.0` pin to fix SSH tunnels broken by the PyMySQL swap (#17).

## [0.1.1] - 2026-05-12

### Changed
- Switched publishing from TestPyPI to production PyPI (#8).

## [0.1.0.1] - 2026-05-12

### Added
- Initial MCP server with a `list_connections` tool.
- `query` tool with a MySQL adapter, connection pooling, and a readonly guard (#2).
- SQLite adapter support (#5).
- Connect to databases via an SSH tunnel (#7).
- CI setup and TestPyPI publish workflow (#13).
