import socket
import threading
from pathlib import Path
from typing import Any

import paramiko

from mcp_sequel.config import SSHTunnelConfig


class SSHTunnel:
    def __init__(
        self,
        local_port: int,
        server_socket: socket.socket,
        client: paramiko.SSHClient,
    ) -> None:
        self.local_bind_port = local_port
        self._server_socket = server_socket
        self._client = client

    def stop(self) -> None:
        self._server_socket.close()
        self._client.close()


def _relay(src: Any, dst: Any) -> None:
    try:
        while data := src.recv(4096):
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            src.close()
        except Exception:
            pass


def _handle(chan: paramiko.Channel, sock: socket.socket) -> None:
    threading.Thread(target=_relay, args=(chan, sock), daemon=True).start()
    threading.Thread(target=_relay, args=(sock, chan), daemon=True).start()


def open_tunnel(
    ssh_cfg: SSHTunnelConfig, remote_host: str, remote_port: int
) -> SSHTunnel:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict = {
        "hostname": ssh_cfg.host,
        "port": ssh_cfg.port,
        "username": ssh_cfg.user,
    }
    if ssh_cfg.key_file:
        connect_kwargs["key_filename"] = str(Path(ssh_cfg.key_file).expanduser())
    if ssh_cfg.password:
        connect_kwargs["password"] = ssh_cfg.password

    client.connect(**connect_kwargs)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    local_port: int = server_sock.getsockname()[1]
    server_sock.listen(5)

    def _accept_loop() -> None:
        while True:
            try:
                conn, addr = server_sock.accept()
            except OSError:
                return
            try:
                transport = client.get_transport()
                assert transport is not None
                chan = transport.open_channel(
                    "direct-tcpip", (remote_host, remote_port), addr
                )
                _handle(chan, conn)
            except Exception:
                conn.close()

    threading.Thread(target=_accept_loop, daemon=True).start()
    return SSHTunnel(local_port, server_sock, client)


def close_tunnel(tunnel: SSHTunnel) -> None:
    tunnel.stop()
