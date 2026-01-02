"""Typed extraction schema: coerce extracted values to their declared types.

An extraction_schema is a flat mapping of field name -> type string, e.g.
``{"price": "number", "in_stock": "boolean", "title": "string"}``.
"""

from __future__ import annotations

import re

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")

_TRUE_WORDS = {"true", "yes", "y", "1", "in stock", "available", "instock"}
_FALSE_WORDS = {"false", "no", "n", "0", "out of stock", "unavailable", "sold out"}


def to_number(value: object) -> float | None:
    """Parse a number from int/float or a messy string like '₹1,299.00'."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    cleaned = value.replace(",", "")  # drop thousands separators
    match = _NUM_RE.search(cleaned)
    return float(match.group()) if match else None


def to_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in _TRUE_WORDS:
            return True
        if v in _FALSE_WORDS:
            return False
    return None


def coerce(value: object, type_name: str) -> object:
    """Best-effort coercion of ``value`` to ``type_name``; None on failure."""
    if value is None:
        return None
    t = (type_name or "string").lower()
    if t in ("string", "str", "text"):
        return str(value).strip()
    if t in ("number", "float", "decimal"):
        return to_number(value)
    if t in ("integer", "int"):
        n = to_number(value)
        return int(n) if n is not None else None
    if t in ("boolean", "bool"):
        return to_bool(value)
    if t in ("list", "array"):
        return value if isinstance(value, list) else [value]
    if t in ("object", "json", "dict"):
        return value if isinstance(value, dict) else None
    # date/datetime and unknown types: keep as a trimmed string.
    return str(value).strip()
