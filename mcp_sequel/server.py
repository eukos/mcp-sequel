from mcp.server.fastmcp import FastMCP

from mcp_sequel.config import load_all

mcp = FastMCP("mcp-sequel")


@mcp.tool()
def list_connections() -> str:
    """List all configured database connections."""
    try:
        connections = load_all()
    except Exception as e:
        return f"ERROR: failed to load configs: {e}"

    if not connections:
        from mcp_sequel.config import config_dir

        return f"No connections configured. Add .json files to: {config_dir()}"

    blocks = []
    for name, cfg in connections:
        host = cfg.host if cfg.port == 3306 else f"{cfg.host}:{cfg.port}"
        location = f"{cfg.user}@{host}"
        if cfg.database:
            location += f"/{cfg.database}"
        readonly = "yes" if cfg.readonly else "no"

        header = f"{name} ({location}) [{cfg.type}], readonly: {readonly}"
        if cfg.description:
            blocks.append(f"{header}\n  {cfg.description}")
        else:
            blocks.append(header)

    return "\n\n".join(blocks)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
