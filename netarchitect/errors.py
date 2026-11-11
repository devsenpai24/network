"""
errors.py — Custom exceptions for NetArchitect.
"""


class PhysicalDistanceViolationError(Exception):
    """Raised when copper media is forced beyond the 100 m IEEE 802.3an limit."""

    def __init__(self, distance: float, medium: str):
        self.distance = distance
        self.medium = medium
        super().__init__(
            f"PhysicalDistanceViolationError: {medium} forced at {distance} m exceeds "
            f"the 100 m IEEE 802.3an limit. Signal attenuation at this distance will "
            f"cause excessive bit-error rates; use fibre instead."
        )


class AddressSpaceExhaustedError(Exception):
    """Raised when subnets cannot fit inside the root prefix."""

    def __init__(self, root_prefix: str, requested: int):
        self.root_prefix = root_prefix
        self.requested = requested
        super().__init__(
            f"AddressSpaceExhaustedError: Cannot fit {requested} additional hosts "
            f"inside root prefix {root_prefix}. Address space exhausted."
        )


class InvalidInputError(Exception):
    """Raised when user-supplied input fails validation."""

    def __init__(self, field: str, value, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(
            f"InvalidInputError: field='{field}', value={value!r} — {reason}"
        )
