"""
routing.py — Routing-protocol selection engine for NetArchitect.

Implements select_routing(num_subnets, num_as, has_cloud, links) which
returns a Decision(choice, justification) namedtuple.
"""
from netarchitect.media import Decision  # reuse the same namedtuple


def select_routing(
    num_subnets: int,
    num_as: int,
    has_cloud: bool,
    links: list,
) -> Decision:
    """
    Select the most appropriate routing protocol(s) for the described network.

    Decision rules
    --------------
    1. Single-AS, fewer than 50 subnets, no cloud:
       → OSPF Area 0 (single-area)
         RFC 2328 — link-state, fast convergence via SPF, loop-free.

    2. Multi-AS (num_as > 1) OR cloud presence OR multi-site >50 subnets:
       → Multi-area OSPF + eBGP
         RFC 2328 (OSPF) + RFC 4271 (BGP-4)
         Rationale: routing-domain isolation, route summarisation at ABRs,
         eBGP for inter-AS / cloud exchange.

    Parameters
    ----------
    num_subnets : int  — total number of subnets in the topology
    num_as      : int  — number of autonomous systems
    has_cloud   : bool — True if a cloud VPC / provider attachment exists
    links       : list — link descriptors (not used in protocol selection)

    Returns
    -------
    Decision namedtuple(choice, justification)
    """
    multi_area_triggers = num_as > 1 or has_cloud or num_subnets >= 50

    if not multi_area_triggers:
        # ── Single-area OSPF ──────────────────────────────────────────────────
        return Decision(
            choice="OSPF Area 0",
            justification=(
                f"Single autonomous system (num_as={num_as}), {num_subnets} subnets "
                f"(< 50 threshold), no cloud attachment. "
                f"OSPF (RFC 2328) Area 0 is sufficient: Dijkstra SPF provides fast "
                f"intra-area convergence, loop-free topology, and low overhead for "
                f"this scale. No inter-AS routing or area hierarchy needed."
            ),
        )

    # ── Multi-area OSPF + eBGP ────────────────────────────────────────────────
    reasons = []
    if num_as > 1:
        reasons.append(f"multiple autonomous systems ({num_as} ASes require eBGP inter-AS routing per RFC 4271)")
    if has_cloud:
        reasons.append("cloud VPC attachment (eBGP used for cloud provider peering, e.g. AWS Transit Gateway or Azure ExpressRoute)")
    if num_subnets >= 50:
        reasons.append(f"{num_subnets} subnets ≥ 50 (multi-area OSPF reduces SPF domain size and enables ABR summarisation)")

    justification = (
        f"Triggered by: {'; '.join(reasons)}. "
        f"Multi-area OSPF (RFC 2328) partitions the routing domain into areas, "
        f"reducing SPF computation scope and enabling route summarisation at Area "
        f"Border Routers (ABRs). eBGP (RFC 4271) handles inter-AS path exchange "
        f"and cloud provider peering with full policy control (route-maps, "
        f"local-preference, MED). Together they provide routing-domain isolation, "
        f"scalable summarisation, and policy-based inter-domain routing."
    )

    return Decision(
        choice="Multi-area OSPF + eBGP",
        justification=justification,
    )
