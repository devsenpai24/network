"""
validator.py — Input validation for NetArchitect custom JSON parameters.
"""
import re
from netarchitect.errors import InvalidInputError


def _is_valid_cidr(prefix: str) -> bool:
    """Return True if *prefix* is a valid IPv4 CIDR string like '10.0.0.0/16'."""
    pattern = re.compile(
        r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})$'
    )
    m = pattern.match(prefix)
    if not m:
        return False
    octets = [int(m.group(i)) for i in range(1, 5)]
    if any(o > 255 for o in octets):
        return False
    prefix_len = int(m.group(5))
    if prefix_len > 32:
        return False
    return True


def validate_distance(value) -> float:
    """Validate that *value* is a positive integer or float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidInputError("distance", value, "must be a numeric type (int or float)")
    if value <= 0:
        raise InvalidInputError("distance", value, "must be greater than 0")
    return float(value)


def validate_hosts(value) -> int:
    """Validate that *value* is a positive integer."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidInputError("hosts", value, "must be a positive integer")
    if value <= 0:
        raise InvalidInputError("hosts", value, "must be greater than 0")
    return value


def validate_prefix(value: str) -> str:
    """Validate that *value* is a valid CIDR string."""
    if not isinstance(value, str):
        raise InvalidInputError("prefix", value, "must be a string in CIDR notation (e.g. '10.0.0.0/16')")
    if not _is_valid_cidr(value):
        raise InvalidInputError("prefix", value, "not a valid CIDR notation; expected 'A.B.C.D/P'")
    return value


def validate_custom_input(params: dict) -> dict:
    """
    Validate a full custom-input dictionary.

    Expected keys: distance, hosts, prefix (all optional individually but
    validated when present).  Returns a cleaned copy.
    """
    cleaned = {}
    if "distance" in params:
        cleaned["distance"] = validate_distance(params["distance"])
    if "hosts" in params:
        cleaned["hosts"] = validate_hosts(params["hosts"])
    if "prefix" in params:
        cleaned["prefix"] = validate_prefix(params["prefix"])
    # Pass through any other keys untouched
    for k, v in params.items():
        if k not in cleaned:
            cleaned[k] = v
    return cleaned
