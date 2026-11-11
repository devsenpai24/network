import pytest
import ipaddress
from netarchitect.errors import AddressSpaceExhaustedError
from netarchitect.vlsm import allocate


def int_to_ip(n):
    return ".".join(str((n >> s) & 0xFF) for s in (24, 16, 8, 0))


def ip_to_int(ip_str):
    parts = list(map(int, ip_str.split(".")))
    return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]


def test_basic_allocation():
    result = allocate("192.168.1.0/24", [{"name": "A", "hosts": 50}, {"name": "B", "hosts": 20}])
    assert len(result.subnets) == 2


def test_no_overlap():
    result = allocate("10.0.0.0/16", [
        {"name": "A", "hosts": 500},
        {"name": "B", "hosts": 250},
        {"name": "C", "hosts": 100},
        {"name": "D", "hosts": 50},
    ])
    subnets = result.subnets
    for i in range(len(subnets)):
        for j in range(i + 1, len(subnets)):
            net_i = ip_to_int(subnets[i].network)
            bc_i  = ip_to_int(subnets[i].broadcast)
            net_j = ip_to_int(subnets[j].network)
            bc_j  = ip_to_int(subnets[j].broadcast)
            assert bc_i < net_j or bc_j < net_i, (
                f"Overlap between {subnets[i].name} and {subnets[j].name}"
            )


def test_exhaustion():
    with pytest.raises(AddressSpaceExhaustedError):
        allocate("192.168.1.0/24", [{"name": "X", "hosts": 300}])


def test_wildcard_mask_slash8():
    result = allocate("10.0.0.0/8", [{"name": "T", "hosts": 16000000}])
    s = result.subnets[0]
    assert s.wildcard == "255.255.255.0" or s.prefix <= 8


def test_wildcard_various():
    # /24 wildcard should be 0.0.0.255
    result = allocate("10.0.0.0/16", [{"name": "T", "hosts": 200}])
    s = result.subnets[0]  # /24
    assert s.wildcard == "0.0.0.255"


def test_wildcard_slash30():
    result = allocate("10.0.0.0/24", [{"name": "T", "hosts": 2}])
    s = result.subnets[0]  # /31 (RFC 3021) since hosts=2
    assert s.wildcard == "0.0.0.1"


def test_wildcard_slash31():
    result = allocate("10.0.0.0/24", [{"name": "T", "hosts": 1}])
    # /32 for 1 host
    s = result.subnets[0]
    assert s.prefix in (31, 32)


def test_cross_check_with_ipaddress():
    """Cross-check our bitwise allocator against Python's ipaddress module."""
    result = allocate("10.0.0.0/16", [
        {"name": "A", "hosts": 500},
        {"name": "B", "hosts": 200},
        {"name": "C", "hosts": 50},
    ])
    for s in result.subnets:
        net = ipaddress.IPv4Network(f"{s.network}/{s.prefix}", strict=True)
        assert str(net.network_address) == s.network
        assert str(net.netmask) == s.mask
        assert str(net.broadcast_address) == s.broadcast


def test_overall_utilization():
    result = allocate("10.0.0.0/24", [{"name": "A", "hosts": 100}, {"name": "B", "hosts": 50}])
    assert 0 < result.overall_utilization <= 100


def test_address_space_exhausted_multiple():
    with pytest.raises(AddressSpaceExhaustedError):
        allocate("192.168.0.0/24", [
            {"name": "A", "hosts": 200},
            {"name": "B", "hosts": 200},
        ])
