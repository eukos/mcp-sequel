from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_sequel.config import SSHTunnelConfig
from mcp_sequel.tunnel import close_tunnel, open_tunnel


def test_open_tunnel_with_key_file():
    ssh_cfg = SSHTunnelConfig(
        host="bastion.example.com", user="ubuntu", key_file="~/.ssh/id_rsa"
    )
    mock_tunnel = MagicMock()
    mock_tunnel.local_bind_port = 54321

    with patch(
        "mcp_sequel.tunnel.SSHTunnelForwarder", return_value=mock_tunnel
    ) as mock_cls:
        result = open_tunnel(ssh_cfg, "db.internal", 3306)

    expected_pkey = str(Path("~/.ssh/id_rsa").expanduser())
    mock_cls.assert_called_once_with(
        ("bastion.example.com", 22),
        ssh_username="ubuntu",
        remote_bind_address=("db.internal", 3306),
        ssh_pkey=expected_pkey,
    )
    mock_tunnel.start.assert_called_once()
    assert result is mock_tunnel


def test_open_tunnel_with_password():
    ssh_cfg = SSHTunnelConfig(
        host="bastion.example.com", user="ubuntu", password="sshpass"
    )
    mock_tunnel = MagicMock()

    with patch(
        "mcp_sequel.tunnel.SSHTunnelForwarder", return_value=mock_tunnel
    ) as mock_cls:
        open_tunnel(ssh_cfg, "db.internal", 3306)

    _, kwargs = mock_cls.call_args
    assert kwargs["ssh_password"] == "sshpass"
    assert "ssh_pkey" not in kwargs


def test_open_tunnel_non_standard_ssh_port():
    ssh_cfg = SSHTunnelConfig(
        host="bastion.example.com", port=2222, user="ubuntu", key_file="~/.ssh/id_rsa"
    )
    mock_tunnel = MagicMock()

    with patch(
        "mcp_sequel.tunnel.SSHTunnelForwarder", return_value=mock_tunnel
    ) as mock_cls:
        open_tunnel(ssh_cfg, "db.internal", 3306)

    args, _ = mock_cls.call_args
    assert args[0] == ("bastion.example.com", 2222)


def test_close_tunnel():
    mock_tunnel = MagicMock()
    close_tunnel(mock_tunnel)
    mock_tunnel.stop.assert_called_once()
