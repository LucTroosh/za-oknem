from types import SimpleNamespace

import pytest

from app.rate_limit import RateLimiter, client_key


def _req(host):
    return SimpleNamespace(client=SimpleNamespace(host=host))


@pytest.mark.parametrize(
    ("host", "key"),
    [
        ("203.0.113.7", "203.0.113.7"),
        ("2001:db8:1:2:aaaa:bbbb:cccc:dddd", "2001:db8:1:2::/64"),
        ("2001:db8:1:2:1111:2222:3333:4444", "2001:db8:1:2::/64"),  # same /64, same bucket
        ("testclient", "testclient"),
    ],
)
def test_client_key_collapses_ipv6_to_its_64(host, key):
    assert client_key(_req(host)) == key


def test_client_key_without_client():
    assert client_key(SimpleNamespace(client=None)) == "unknown"


def test_refund_gives_back_the_newest_hit():
    rl = RateLimiter(limit=1, window_seconds=60)
    rl.check("k")
    rl.refund("k")
    rl.check("k")  # would be 429 without the refund
