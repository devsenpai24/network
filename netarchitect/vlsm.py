"""
vlsm.py — Variable-Length Subnet Mask allocator for NetArchitect.

IMPORTANT: This module uses ONLY pure bitwise integer arithmetic.
           `import ipaddress` is intentionally absent.

Algorithm overview:
  1. Parse root prefix string "A.B.C.D/P" with string split + bit-shift math.
  2. Sort requested subnets largest-first (most hosts first) to minimise waste.
  3. For each subnet find the smallest prefix length P such that
     (1 << (32-P)) - 2 >= hosts  (honouring RFC 3021 for /31 and /32).
  4. Align the current allocation pointer to the block boundary.
  5. Check the subnet fits inside the root broadcast address.
  6. Record all addressing details as a SubnetAlloc namedtuple.
  7. Return an AllocationResult namedtuple with subnets + overall utilisation.
"""

from collections import namedtuple
from netarchitect.errors import AddressSpaceExhaustedError

# ── Return types ──────────────────────────────────────────────────────────────
SubnetAlloc = namedtuple(
    "SubnetAlloc",
    [
        "name",          # subnet label
        "network",       # dotted-decimal network address
        "prefix",        # integer prefix length
        "mask",          # dotted-decimal subnet mask
        "wildcard",      # dotted-decimal wildcard mask (for OSPF etc.)
        "broadcast",     # dotted-decimal broadcast address
        "gateway",       # dotted-decimal default gateway (network+1, or network for /31)
        "first_usable",  # dotted-decimal first usable host
        "last_usable",   # dotted-decimal last usable host
        "usable_hosts",  # integer count of usable host addresses
        "utilization_pct",  # float — hosts_requested / usable_hosts * 100
    ],
)

AllocationResult = namedtuple(
    "AllocationResult",
    [
        "subnets",             # list[SubnetAlloc]
        "overall_utilization", # float — total_requested / total_usable_in_root * 100
    ],
)


# ── Bitwise helper functions ──────────────────────────────────────────────────

def _dotted_to_int(ip_str: str) -> int:
    """
    Convert a dotted-decimal IPv4 string to a 32-bit integer using bit-shifts.

    "192.168.1.0"  →  (192 << 24) | (168 << 16) | (1 << 8) | 0
                    =  0xC0A80100
    """
    parts = ip_str.split(".")
    # Each octet occupies 8 bits; first octet is most-significant (bits 31-24)
    return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])


def _int_to_dotted(n: int) -> str:
    """
    Convert a 32-bit integer to dotted-decimal string using bit-shifts and masking.

    0xC0A80100  →  "192.168.1.0"

    We right-shift by 24/16/8/0 bits, then AND with 0xFF to isolate each octet.
    """
    return (
        f"{(n >> 24) & 0xFF}"   # bits 31-24 → first octet
        f".{(n >> 16) & 0xFF}"  # bits 23-16 → second octet
        f".{(n >> 8) & 0xFF}"   # bits 15-8  → third octet
        f".{n & 0xFF}"          # bits 7-0   → fourth octet
    )


def _prefix_to_mask_int(prefix_len: int) -> int:
    """
    Build a 32-bit subnet mask integer from a prefix length.

    /24 → 0xFFFFFF00 (24 ones, 8 zeros)

    Trick: left-shift all ones (0xFFFFFFFF + 1 = 0x100000000) by (32 - prefix_len),
    then mask to 32 bits.  Equivalently: (0xFFFFFFFF << (32 - p)) & 0xFFFFFFFF.

    Special case /0: shifting by 32 is undefined behaviour in some languages;
    in Python int shifting is arbitrary-precision, so we guard explicitly.
    """
    if prefix_len == 0:
        return 0x00000000  # no bits set → entire address space
    return (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF


def _find_prefix_for_hosts(hosts: int) -> int:
    """
    Find the smallest (most specific) prefix length P such that
    the subnet can accommodate at least *hosts* usable addresses.

    Special RFC cases:
      /32 → 1 usable address (loopback / host route)
      /31 → 2 usable addresses (RFC 3021 point-to-point)
      /30 → 2 usable addresses (traditional p-t-p, wastes 2)
      /P  → (1 << (32-P)) - 2 usable for P < 31

    We iterate P from 32 down to 0, stopping when capacity ≥ hosts.
    """
    if hosts == 1:
        return 32  # /32 loopback

    if hosts <= 2:
        return 31  # /31 RFC 3021 p-t-p (2 usable)

    # For /30 and smaller: usable = block_size - 2
    for prefix_len in range(30, -1, -1):
        # block_size = total addresses in this prefix block
        block_size = 1 << (32 - prefix_len)   # e.g. /24 → 256
        usable = block_size - 2               # subtract network + broadcast
        if usable >= hosts:
            return prefix_len

    # /0 can hold ~4 billion addresses; if we get here hosts is unreasonably large
    return 0


def _usable_count(prefix_len: int) -> int:
    """Return usable host count for a given prefix length (RFC 3021 aware)."""
    if prefix_len == 32:
        return 1
    if prefix_len == 31:
        return 2
    # /30 and larger blocks: subtract network address + broadcast
    return (1 << (32 - prefix_len)) - 2


# ── Main allocation function ──────────────────────────────────────────────────

def allocate(root_prefix_str: str, subnets_list: list) -> AllocationResult:
    """
    Perform VLSM allocation inside *root_prefix_str* for the requested subnets.

    Parameters
    ----------
    root_prefix_str : str
        Root address space, e.g. "10.0.0.0/16".
    subnets_list : list[dict]
        Each dict has keys "name" (str) and "hosts" (int).

    Returns
    -------
    AllocationResult namedtuple.

    Raises
    ------
    AddressSpaceExhaustedError
        When a subnet block would overflow the root broadcast address.
    """
    # ── Step 1: Parse root prefix ─────────────────────────────────────────────
    # Split "10.0.0.0/16" into the IP part and the prefix-length part
    ip_part, prefix_part = root_prefix_str.split("/")
    root_prefix_len = int(prefix_part)

    # Convert dotted-decimal to 32-bit integer
    root_network_int = _dotted_to_int(ip_part)

    # Root block size = 2^(32 - root_prefix_len)
    root_block_size = 1 << (32 - root_prefix_len)

    # Root broadcast = last address in the root block
    # Bit trick: OR the network address with the host-bits all set to 1
    # host_mask has 1s in the lower (32 - root_prefix_len) bits
    root_host_mask    = root_block_size - 1          # e.g. /16 → 0x0000FFFF
    root_broadcast_int = root_network_int | root_host_mask

    # Total usable in root (for overall-utilisation denominator)
    total_usable_in_root = _usable_count(root_prefix_len)

    # ── Step 2: Sort subnets largest-first ───────────────────────────────────
    # Placing larger blocks first minimises alignment gaps (best-fit heuristic)
    sorted_subnets = sorted(subnets_list, key=lambda s: s["hosts"], reverse=True)

    # ── Allocation loop ───────────────────────────────────────────────────────
    # current_ptr tracks the next available address (integer)
    current_ptr = root_network_int
    results     = []
    total_hosts_requested = 0

    for subnet in sorted_subnets:
        name           = subnet["name"]
        hosts_requested = subnet["hosts"]
        total_hosts_requested += hosts_requested

        # ── Step 3: Find smallest fitting prefix ─────────────────────────────
        prefix_len = _find_prefix_for_hosts(hosts_requested)
        usable     = _usable_count(prefix_len)

        # block_size is the total number of addresses in this subnet block
        # For /24 → 256, /25 → 128, /30 → 4, /31 → 2, /32 → 1
        block_size = 1 << (32 - prefix_len)

        # ── Step 4: Align current_ptr to the block boundary ──────────────────
        # A /24 block must start on a multiple of 256, a /25 on a multiple of 128.
        # Formula: round *current_ptr* up to the nearest multiple of block_size.
        #   (current_ptr + block_size - 1)  clears any existing alignment
        #   & ~(block_size - 1)             masks out the lower log2(block_size) bits
        # Because block_size is always a power of 2, (block_size - 1) is an all-ones
        # bitmask for the lower bits, and ~(block_size - 1) zeros those bits out.
        current_ptr = (current_ptr + block_size - 1) & ~(block_size - 1)

        # ── Step 5: Check address-space exhaustion ───────────────────────────
        # The last address of this block would be: current_ptr + block_size - 1
        # If that exceeds the root broadcast, we're out of space.
        if (current_ptr + block_size - 1) > root_broadcast_int:
            raise AddressSpaceExhaustedError(
                root_prefix=root_prefix_str,
                requested=hosts_requested,
            )

        # ── Step 6: Compute all addressing fields ────────────────────────────
        network_int   = current_ptr
        broadcast_int = current_ptr + block_size - 1  # last addr in block

        if prefix_len == 32:
            # /32 — single host route / loopback; no traditional gateway concept
            gateway_int      = network_int
            first_usable_int = network_int
            last_usable_int  = network_int
        elif prefix_len == 31:
            # RFC 3021 /31 — both addresses usable on a p-t-p link
            gateway_int      = network_int      # lower address acts as gateway
            first_usable_int = network_int
            last_usable_int  = broadcast_int    # = network_int + 1
        else:
            # Normal subnets: network addr and broadcast addr are reserved
            gateway_int      = network_int + 1   # first usable = default gateway
            first_usable_int = network_int + 1
            last_usable_int  = broadcast_int - 1

        # ── Step 7: Build dotted-decimal strings ──────────────────────────────
        network_str       = _int_to_dotted(network_int)
        broadcast_str     = _int_to_dotted(broadcast_int)
        gateway_str       = _int_to_dotted(gateway_int)
        first_usable_str  = _int_to_dotted(first_usable_int)
        last_usable_str   = _int_to_dotted(last_usable_int)

        # ── Step 8: Subnet mask and wildcard mask ────────────────────────────
        # Subnet mask: prefix_len ones followed by (32 - prefix_len) zeros
        mask_int     = _prefix_to_mask_int(prefix_len)
        mask_str     = _int_to_dotted(mask_int)

        # Wildcard mask: bitwise NOT of subnet mask, restricted to 32 bits.
        # (~mask_int) in Python gives a negative number (arbitrary-precision int),
        # so we AND with 0xFFFFFFFF to keep only the lower 32 bits.
        wildcard_int = (~mask_int) & 0xFFFFFFFF
        wildcard_str = _int_to_dotted(wildcard_int)

        # ── Step 9: Utilisation ───────────────────────────────────────────────
        utilization_pct = (hosts_requested / usable) * 100.0

        results.append(
            SubnetAlloc(
                name=name,
                network=network_str,
                prefix=prefix_len,
                mask=mask_str,
                wildcard=wildcard_str,
                broadcast=broadcast_str,
                gateway=gateway_str,
                first_usable=first_usable_str,
                last_usable=last_usable_str,
                usable_hosts=usable,
                utilization_pct=round(utilization_pct, 2),
            )
        )

        # Advance pointer past the end of this block
        current_ptr = broadcast_int + 1

    # ── Overall utilisation ───────────────────────────────────────────────────
    overall_utilization = (total_hosts_requested / total_usable_in_root) * 100.0

    return AllocationResult(
        subnets=results,
        overall_utilization=round(overall_utilization, 4),
    )
