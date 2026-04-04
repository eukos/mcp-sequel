import datetime
import decimal

import pytest

from mcp_sequel.adapters.base import _serialize


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
