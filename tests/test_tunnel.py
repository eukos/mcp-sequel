import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_sequel.config import SSHTunnelConfig
from mcp_sequel.tunnel import SSHTunnel, close_tunnel, open_tunnel


def _make_mock_client(local_port=54321):
    mock_client = MagicMock()
    mock_transport = MagicMock()
    mock_client.get_transport.return_value = mock_transport
    return mock_client


def _patch_socket(local_port=54321):
    mock_sock = MagicMock(spec=socket.socket)
    mock_sock.getsockname.return_value = ("127.0.0.1", local_port)
    mock_sock.accept.side_effect = OSError("mock closed")
    return mock_sock


def test_open_tunnel_with_key_file():
    ssh_cfg = SSHTunnelConfig(
        host="bastion.example.com", user="ubuntu", key_file="~/.ssh/id_rsa"
    )
    mock_client = _make_mock_client()
    mock_sock = _patch_socket(54321)

    with patch("mcp_sequel.tunnel.paramiko.SSHClient", return_value=mock_client):
        with patch("mcp_sequel.tunnel.socket.socket", return_value=mock_sock):
            result = open_tunnel(ssh_cfg, "db.internal", 3306)

    expected_pkey = str(Path("~/.ssh/id_rsa").expanduser())
    mock_client.connect.assert_called_once_with(
        hostname="bastion.example.com",
        port=22,
        username="ubuntu",
        key_filename=expected_pkey,
    )
    assert result.local_bind_port == 54321


def test_open_tunnel_with_password():
    ssh_cfg = SSHTunnelConfig(
        host="bastion.example.com", user="ubuntu", password="sshpass"
    )
    mock_client = _make_mock_client()
    mock_sock = _patch_socket()

    with patch("mcp_sequel.tunnel.paramiko.SSHClient", return_value=mock_client):
        with patch("mcp_sequel.tunnel.socket.socket", return_value=mock_sock):
            open_tunnel(ssh_cfg, "db.internal", 3306)

    _, kwargs = mock_client.connect.call_args
    assert kwargs["password"] == "sshpass"
    assert "key_filename" not in kwargs


def test_open_tunnel_non_standard_ssh_port():
    ssh_cfg = SSHTunnelConfig(
        host="bastion.example.com", port=2222, user="ubuntu", key_file="~/.ssh/id_rsa"
    )
    mock_client = _make_mock_client()
    mock_sock = _patch_socket()

    with patch("mcp_sequel.tunnel.paramiko.SSHClient", return_value=mock_client):
        with patch("mcp_sequel.tunnel.socket.socket", return_value=mock_sock):
            open_tunnel(ssh_cfg, "db.internal", 3306)

    _, kwargs = mock_client.connect.call_args
    assert kwargs["port"] == 2222


def test_close_tunnel():
    mock_client = MagicMock()
    mock_sock = MagicMock()
    tunnel = SSHTunnel(local_port=54321, server_socket=mock_sock, client=mock_client)

    close_tunnel(tunnel)

    mock_sock.close.assert_called_once()
    mock_client.close.assert_called_once()
