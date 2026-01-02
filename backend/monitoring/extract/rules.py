"""Deterministic, zero-cost extractors for common fields (price, availability).

These run before any LLM call; the LLM only fills fields the rules can't cover.
"""

from __future__ import annotations

import re

from .schema import to_number

# Currency symbol/code followed by an amount.
_PRICE_RE = re.compile(
    r"(?:₹|rs\.?|inr|\$|usd|€|eur|£|gbp)\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    re.IGNORECASE,
)

_IN_STOCK = ("in stock", "instock", "add to cart", "buy now", "available")
_OUT_OF_STOCK = ("out of stock", "sold out", "currently unavailable", "unavailable")

# Field-name hints that map a schema field to a rule.
_PRICE_HINTS = ("price", "amount", "cost", "fee", "fare")
_STOCK_HINTS = ("stock", "availab", "in_stock", "instock")
_NUMERIC_TYPES = ("number", "float", "integer", "int", "decimal")
_BOOL_TYPES = ("boolean", "bool")


def extract_price(text: str) -> float | None:
    match = _PRICE_RE.search(text or "")
    return to_number(match.group(1)) if match else None


def extract_availability(text: str) -> bool | None:
    lowered = (text or "").lower()
    if any(k in lowered for k in _OUT_OF_STOCK):
        return False
    if any(k in lowered for k in _IN_STOCK):
        return True
    return None


def rule_extract(text: str, schema: dict[str, str]) -> dict[str, object]:
    """Fill the schema fields the heuristics can handle; leave the rest absent."""
    out: dict[str, object] = {}
    for field, type_name in schema.items():
        name = field.lower()
        tn = (type_name or "").lower()
        if tn in _NUMERIC_TYPES and any(h in name for h in _PRICE_HINTS):
            out[field] = extract_price(text)
        elif tn in _BOOL_TYPES and any(h in name for h in _STOCK_HINTS):
            out[field] = extract_availability(text)
    return out
