from mcp_sequel.config import MySQLConfig, SSHTunnelConfig


def test_ssh_tunnel_config_with_key_file():
    cfg = MySQLConfig(
        type="mysql",
        host="db.internal",
        port=3306,
        user="root",
        password="secret",
        ssh_tunnel={
            "host": "bastion.example.com",
            "user": "ubuntu",
            "key_file": "~/.ssh/id_rsa",
        },
    )
    assert cfg.ssh_tunnel is not None
    assert cfg.ssh_tunnel.host == "bastion.example.com"
    assert cfg.ssh_tunnel.port == 22
    assert cfg.ssh_tunnel.user == "ubuntu"
    assert cfg.ssh_tunnel.key_file == "~/.ssh/id_rsa"
    assert cfg.ssh_tunnel.password is None


def test_ssh_tunnel_config_with_password():
    cfg = MySQLConfig(
        type="mysql",
        host="db.internal",
        port=3306,
        user="root",
        password="secret",
        ssh_tunnel={
            "host": "bastion.example.com",
            "user": "ubuntu",
            "password": "sshpass",
        },
    )
    assert cfg.ssh_tunnel.password == "sshpass"
    assert cfg.ssh_tunnel.key_file is None


def test_ssh_tunnel_non_standard_port():
    tunnel = SSHTunnelConfig(
        host="bastion.example.com", user="ubuntu", port=2222, key_file="~/.ssh/id_rsa"
    )
    assert tunnel.port == 2222


def test_mysql_config_without_ssh_tunnel():
    cfg = MySQLConfig(
        type="mysql", host="localhost", port=3306, user="root", password="secret"
    )
    assert cfg.ssh_tunnel is None


def test_location_with_ssh_tunnel():
    cfg = MySQLConfig(
        type="mysql",
        host="db.internal",
        port=3306,
        user="reader",
        password="secret",
        database="myapp",
        ssh_tunnel={
            "host": "bastion.example.com",
            "user": "ubuntu",
            "key_file": "~/.ssh/id_rsa",
        },
    )
    assert cfg.location == "ubuntu@bastion.example.com -> reader@db.internal/myapp"


def test_location_without_ssh_tunnel():
    cfg = MySQLConfig(
        type="mysql", host="localhost", port=3306, user="root", password="secret"
    )
    assert cfg.location == "root@localhost"


def test_location_ssh_tunnel_non_standard_port():
    cfg = MySQLConfig(
        type="mysql",
        host="db.internal",
        port=3306,
        user="reader",
        password="secret",
        ssh_tunnel={
            "host": "bastion.example.com",
            "port": 2222,
            "user": "ubuntu",
            "key_file": "~/.ssh/id_rsa",
        },
    )
    assert cfg.location == "ubuntu@bastion.example.com:2222 -> reader@db.internal"
