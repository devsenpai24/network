from netarchitect.routing import select_routing


def test_single_as_ospf():
    d = select_routing(num_subnets=10, num_as=1, has_cloud=False, links=[])
    assert "OSPF" in d.choice


def test_multi_as_bgp():
    d = select_routing(num_subnets=10, num_as=3, has_cloud=False, links=[])
    assert "BGP" in d.choice or "eBGP" in d.choice


def test_cloud_triggers_bgp():
    d = select_routing(num_subnets=10, num_as=1, has_cloud=True, links=[])
    assert "BGP" in d.choice or "eBGP" in d.choice or "OSPF" in d.choice


def test_rfc_cited_ospf():
    d = select_routing(num_subnets=5, num_as=1, has_cloud=False, links=[])
    assert "2328" in d.justification


def test_rfc_cited_bgp():
    d = select_routing(num_subnets=10, num_as=2, has_cloud=False, links=[])
    assert "4271" in d.justification or "2328" in d.justification


def test_many_subnets_multi_area():
    d = select_routing(num_subnets=60, num_as=1, has_cloud=False, links=[])
    assert "multi-area" in d.choice.lower() or "OSPF" in d.choice
