"""
media.py — Physical-layer media selection for NetArchitect.

Implements select_media(distance_m, force_copper=False) which returns a
Decision namedtuple(choice, justification) according to IEEE standards.
"""
from collections import namedtuple
from netarchitect.errors import PhysicalDistanceViolationError

Decision = namedtuple("Decision", ["choice", "justification"])

# ── Optical parameters ────────────────────────────────────────────────────────
_TX_POWER_DBM = 0.5          # dBm — typical 10GBASE-LR/ER launch power
_RX_SENS_LR   = -14.4        # dBm — 10GBASE-LR receiver sensitivity
_RX_SENS_ER   = -15.8        # dBm — 10GBASE-ER receiver sensitivity
_FIBER_LOSS   = 0.4          # dB/km — OS2 SMF attenuation at 1310/1550 nm
_CONN_LOSS    = 0.5          # dB per connector
_CONNECTORS   = 2            # connectors per link (one at each end)


def _optical_budget(distance_m: float, rx_sens: float, transceiver: str) -> str:
    """Return a detailed optical-budget justification string."""
    distance_km = distance_m / 1000.0
    link_loss   = distance_km * _FIBER_LOSS + _CONNECTORS * _CONN_LOSS
    budget      = _TX_POWER_DBM - rx_sens
    margin      = budget - link_loss

    return (
        f"{transceiver} on OS2 SMF. "
        f"Distance: {distance_m} m ({distance_km:.3f} km). "
        f"Optical power budget: Tx={_TX_POWER_DBM:+.1f} dBm, "
        f"Rx sensitivity={rx_sens:.1f} dBm, "
        f"budget={budget:.2f} dB. "
        f"Link loss: {distance_km:.3f} km × {_FIBER_LOSS} dB/km "
        f"+ {_CONNECTORS} connectors × {_CONN_LOSS} dB = {link_loss:.2f} dB. "
        f"Power margin: {margin:.2f} dB ({'OK' if margin >= 0 else 'INSUFFICIENT — use amplifier/EDFA'})."
    )


def select_media(distance_m: float, force_copper: bool = False) -> Decision:
    """
    Select the appropriate physical medium for a link of *distance_m* metres.

    Parameters
    ----------
    distance_m   : Link length in metres (must be > 0).
    force_copper : If True and distance_m > 100, raise PhysicalDistanceViolationError.

    Returns
    -------
    Decision namedtuple with .choice (medium + transceiver) and .justification.
    """
    if distance_m <= 100:
        # ── Copper zone (≤100 m) ──────────────────────────────────────────
        # IEEE 802.3an-2006 specifies 10GBASE-T up to 100 m on Cat6a UTP.
        return Decision(
            choice="Cat6a UTP / 10GBASE-T",
            justification=(
                f"Distance {distance_m} m is within the 100 m IEEE 802.3an "
                f"10GBASE-T limit on Cat6a UTP. No optical transceiver needed; "
                f"PoE+ (802.3at) or PoE++ (802.3bt) can be delivered over the same cable."
            ),
        )

    # Distance > 100 m — copper is physically out of spec
    if force_copper:
        raise PhysicalDistanceViolationError(
            distance=distance_m,
            medium="Cat6a UTP / 10GBASE-T",
        )

    if distance_m <= 400:
        # ── Multi-mode fibre zone (101–400 m) ────────────────────────────
        # OM4 MMF with 10GBASE-SR (850 nm VCSEL): 400 m reach per IEEE 802.3ae.
        # Exceeding 400 m causes modal dispersion → ISI → excessive BER.
        return Decision(
            choice="OM4 MMF / 10GBASE-SR",
            justification=(
                f"Distance {distance_m} m exceeds copper limit (100 m) but is within "
                f"the 400 m 850 nm reach of OM4 MMF with 10GBASE-SR (IEEE 802.3ae). "
                f"Modal dispersion at 850 nm limits OM4 to 400 m at 10 Gbps; "
                f"OS2 SMF would be over-engineered here."
            ),
        )

    # Distance > 400 m — single-mode fibre required
    # 10GBASE-LR: up to 10 km (10 000 m) at 1310 nm
    # 10GBASE-ER: up to 40 km (40 000 m) at 1550 nm
    if distance_m <= 10_000:
        transceiver = "10GBASE-LR"
        rx_sens     = _RX_SENS_LR
    else:
        transceiver = "10GBASE-ER"
        rx_sens     = _RX_SENS_ER

    justification = _optical_budget(distance_m, rx_sens, transceiver)

    return Decision(
        choice=f"OS2 SMF / {transceiver}",
        justification=justification,
    )
