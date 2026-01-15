"""Hand-labelled evaluation datasets.

CHANGE_CASES: snapshot pairs labelled "meaningful" or "noise". The naive
detector flags any textual difference (so every case is a positive); the
semantic detector should keep the meaningful ones and suppress the noise.

Noise is split into:
  - "easy" cosmetic churn (dates, times, years, session ids, whitespace) that
    normalization collapses, and
  - "hard" churn (rotating banners, reordered/reworded boilerplate) that text
    normalization alone can't suppress — these are the cases embeddings help
    with, so without an LLM key they remain semantic false positives. Keeping
    them makes the false-positive-reduction number realistic, not 100%.

EXTRACTION_CASES: content + schema + expected values for fields the rule-based
extractors handle (price / availability), so the accuracy metric is
reproducible without an LLM.
"""

from __future__ import annotations

ChangeCase = dict
ExtractionCase = dict

_BASE_PROSE = [
    "Welcome to the Acme compliance portal. Our policies are listed below.",
    "Quarterly report published. See the figures and notes for full details.",
    "System status: all services operational. Contact support for assistance.",
    "This page lists the current regulations and guidance for licensed operators.",
    "Product overview and technical specifications for the Widget Pro series.",
]


def _noise_easy() -> list[ChangeCase]:
    cases: list[ChangeCase] = []
    # Date / time / year / session-id churn around identical content.
    for i, txt in enumerate(_BASE_PROSE):
        prev = f"{txt} Last updated 2024-01-0{(i % 9) + 1} 10:3{i}:00. Session a1b2c3d4e5f6a7b8."
        for j in range(8):
            cur = (
                f"{txt} Last updated 2025-0{(j % 9) + 1}-1{j % 9} "
                f"1{j % 9}:4{j % 9}:0{j % 9}. Session {(123456789 + j * 37):016x}."
            )
            cases.append(
                {"label": "noise", "change_type": "content", "prev_text": prev, "cur_text": cur}
            )
    # Whitespace-only churn.
    for txt in _BASE_PROSE:
        cases.append(
            {
                "label": "noise",
                "change_type": "content",
                "prev_text": txt,
                "cur_text": "   " + txt.replace(". ", ".\n\n  ") + "   ",
            }
        )
    # Trailing copyright-year churn.
    for year in range(2018, 2026):
        cases.append(
            {
                "label": "noise",
                "change_type": "content",
                "prev_text": "Acme Corp. All rights reserved. (c) 2017.",
                "cur_text": f"Acme Corp. All rights reserved. (c) {year}.",
            }
        )
    return cases


def _noise_hard() -> list[ChangeCase]:
    cases: list[ChangeCase] = []
    banners = [
        (
            "Featured today: Product A — shop the sale now!",
            "Featured today: Product Z — limited-time offer ends soon!",
        ),
        (
            "Sponsored: try our premium plan free for 30 days.",
            "Sponsored: download the mobile app and save big.",
        ),
        (
            "Trending: 10 tips for spring cleaning your home.",
            "Trending: the best gadgets to buy this summer season.",
        ),
        (
            "Newsletter: sign up for weekly deals and updates.",
            "Newsletter: join 50k readers for daily market insights.",
        ),
        (
            "Ad: book your holiday getaway with exclusive perks.",
            "Ad: refinance your loan at historically low rates today.",
        ),
    ]
    for a, b in banners:
        for suffix in ("", " More below.", " See details."):
            cases.append(
                {
                    "label": "noise",
                    "change_type": "content",
                    "prev_text": a + suffix,
                    "cur_text": b + suffix,
                }
            )
    # Reordered list items (same content, different order).
    items = ["Apples", "Bananas", "Cherries", "Dates", "Elderberries"]
    for k in range(1, 6):
        prev = "Available: " + ", ".join(items)
        cur = "Available: " + ", ".join(items[k:] + items[:k])
        cases.append(
            {"label": "noise", "change_type": "content", "prev_text": prev, "cur_text": cur}
        )
    return cases


def _meaningful() -> list[ChangeCase]:
    cases: list[ChangeCase] = []
    # Price changes (structured field diff -> always meaningful).
    prices = [(1299, 999), (50, 75), (1999, 1499), (29, 39), (100, 100.5), (4999, 3999)]
    for old, new in prices:
        for _ in range(3):
            cases.append(
                {
                    "label": "meaningful",
                    "change_type": "price",
                    "prev_text": f"The price is {old} this period.",
                    "cur_text": f"The price is {new} this period.",
                    "prev_fields": {"price": old},
                    "cur_fields": {"price": new},
                }
            )
    # Availability flips.
    for old, new in [(True, False), (False, True)]:
        for _ in range(5):
            cases.append(
                {
                    "label": "meaningful",
                    "change_type": "availability",
                    "prev_text": "Stock status shown on page.",
                    "cur_text": "Stock status shown on page.",
                    "prev_fields": {"in_stock": old},
                    "cur_fields": {"in_stock": new},
                }
            )
    # Clause / policy rewrites (substantial prose change -> low similarity).
    clauses = [
        (
            "We retain your personal data for 30 days after account closure.",
            "We now share your personal data with third-party advertising partners and retain it for five years.",
        ),
        (
            "Refunds are available within 14 days of purchase, no questions asked.",
            "All sales are final. Refunds are no longer offered under any circumstances.",
        ),
        (
            "This regulation applies to operators with over 500 employees.",
            "This regulation now applies to all operators regardless of headcount, effective immediately.",
        ),
        (
            "Service uptime target is 99.9% measured monthly.",
            "We have removed all uptime guarantees and service credits from this agreement.",
        ),
        (
            "Users may export their data at any time in CSV format.",
            "Data export has been discontinued; stored data may be deleted without notice.",
        ),
    ]
    for a, b in clauses:
        for _ in range(5):
            cases.append(
                {"label": "meaningful", "change_type": "clause", "prev_text": a, "cur_text": b}
            )
    return cases


def change_cases() -> list[ChangeCase]:
    cases = _noise_easy() + _noise_hard() + _meaningful()
    for c in cases:
        c.setdefault("prev_fields", {})
        c.setdefault("cur_fields", {})
    return cases


def extraction_cases() -> list[ExtractionCase]:
    cases: list[ExtractionCase] = []
    price_samples = [
        ("Now only ₹1,299.00 — In stock, buy now!", 1299.0, True),
        ("Special price: $19.99. Out of stock.", 19.99, False),
        ("Was €50, now €39.95. Available today.", 50.0, True),
        ("Price: Rs 2,499 — currently unavailable.", 2499.0, False),
        ("£12.50 per unit. In stock.", 12.5, True),
        ("USD 100 flat rate. Sold out.", 100.0, False),
        ("Offer: ₹999 only. Add to cart now.", 999.0, True),
        ("Cost is $7.49 each — out of stock.", 7.49, False),
    ]
    for text, price, in_stock in price_samples:
        for _ in range(5):
            cases.append(
                {
                    "content": text,
                    "schema": {"price": "number", "in_stock": "boolean"},
                    "expected": {"price": price, "in_stock": in_stock},
                }
            )
    return cases
