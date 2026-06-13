import datetime
import decimal

import pytest

from mcp_sequel.adapters.base import BaseAdapter, _serialize


@pytest.mark.parametrize(
    "value, expected",
    [
        (datetime.date(2025, 12, 25), "2025-12-25"),
        (datetime.datetime(2025, 12, 25, 14, 30, 45), "2025-12-25 14:30:45"),
        (datetime.timedelta(days=1, hours=2, minutes=30), "1 day, 2:30:00"),
        (decimal.Decimal("123.456"), "123.456"),
        (
            decimal.Decimal("0.1") + decimal.Decimal("0.2"),
            str(decimal.Decimal("0.1") + decimal.Decimal("0.2")),
        ),
        (b"\xff\xfe", "fffe"),
        (b"", ""),
        (None, None),
        (42, 42),
        ("text", "text"),
        (3.14, 3.14),
        (True, True),
    ],
)
def test_serialize(value, expected):
    assert _serialize(value) == expected


@pytest.mark.parametrize(
    "conn_name, database, cfg",
    [
        ("myconn", None, None),
        ("myconn", "shop", None),
        ("myconn", "blog", object()),
    ],
)
def test_make_pool_key_default_returns_conn_name(conn_name, database, cfg):
    assert BaseAdapter.make_pool_key(conn_name, database, cfg) == conn_name


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            __import__("uuid").UUID("12345678-1234-5678-1234-567812345678"),
            "12345678-1234-5678-1234-567812345678",
        ),
        (__import__("ipaddress").IPv4Address("192.168.1.1"), "192.168.1.1"),
        (__import__("ipaddress").IPv6Address("::1"), "::1"),
        (__import__("ipaddress").IPv4Network("10.0.0.0/8"), "10.0.0.0/8"),
        (memoryview(b"\xff\xfe"), "fffe"),
        ({"key": 1}, {"key": 1}),
        ([1, 2, 3], [1, 2, 3]),
    ],
)
def test_serialize_postgresql_types(value, expected):
    assert _serialize(value) == expected
