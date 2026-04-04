from pathlib import Path

from sshtunnel import SSHTunnelForwarder

from mcp_sequel.config import SSHTunnelConfig


def open_tunnel(
    ssh_cfg: SSHTunnelConfig, remote_host: str, remote_port: int
) -> SSHTunnelForwarder:
    kwargs: dict = {
        "ssh_username": ssh_cfg.user,
        "remote_bind_address": (remote_host, remote_port),
    }
    if ssh_cfg.key_file:
        kwargs["ssh_pkey"] = str(Path(ssh_cfg.key_file).expanduser())
    if ssh_cfg.password:
        kwargs["ssh_password"] = ssh_cfg.password

    tunnel = SSHTunnelForwarder((ssh_cfg.host, ssh_cfg.port), **kwargs)
    tunnel.start()
    return tunnel


def close_tunnel(tunnel: SSHTunnelForwarder) -> None:
    tunnel.stop()
