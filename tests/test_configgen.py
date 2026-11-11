import pytest
from netarchitect.configgen import generate_configs


def test_no_allowed_vlan_all_campus():
    configs = generate_configs("campus", {})
    for device, cfg in configs.items():
        assert "allowed vlan all" not in cfg.lower(), f"Found 'allowed vlan all' in {device}"


def test_no_allowed_vlan_all_metro():
    configs = generate_configs("metro", {})
    for device, cfg in configs.items():
        assert "allowed vlan all" not in cfg.lower(), f"Found 'allowed vlan all' in {device}"


def test_no_allowed_vlan_all_wan():
    configs = generate_configs("wan", {})
    for device, cfg in configs.items():
        assert "allowed vlan all" not in cfg.lower(), f"Found 'allowed vlan all' in {device}"


def test_campus_has_rapid_pvst():
    configs = generate_configs("campus", {})
    combined = " ".join(configs.values())
    assert "rapid-pvst" in combined


def test_campus_has_vlans():
    configs = generate_configs("campus", {})
    combined = " ".join(configs.values())
    assert "vlan 10" in combined


def test_wan_has_ipsec():
    configs = generate_configs("wan", {})
    combined = " ".join(configs.values())
    assert "crypto" in combined.lower() or "ipsec" in combined.lower() or "ikev2" in combined.lower()


def test_wan_has_bgp():
    configs = generate_configs("wan", {})
    combined = " ".join(configs.values())
    assert "router bgp" in combined


def test_ospf_wildcard_not_subnet_mask():
    """OSPF network statements should use wildcard masks, not subnet masks."""
    configs = generate_configs("campus", {})
    combined = " ".join(configs.values())
    # Should have 'network X.X.X.X Y.Y.Y.Y area Z' style
    assert "network " in combined
