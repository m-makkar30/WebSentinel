"""Impact assessment: classify why a change matters, score severity, alert.

For a meaningful Change, the strong (assess-role) LLM produces a severity, a
plain-language headline, and a "why it matters" explanation. Without an API key
we fall back to a heuristic so alerts still work rule-based.
"""

from __future__ import annotations

import json
import logging
import re

from ..models import Alert, AlertKind, Change, ChangeType, Severity

logger = logging.getLogger(__name__)

TEXT_DIFF_SNIPPET = 1500

_SYSTEM = (
    "You are a monitoring analyst. Assess a detected change to a watched web "
    "page. Respond with ONLY a JSON object: "
    '{"severity": one of "info"|"low"|"medium"|"high"|"critical", '
    '"headline": a short title (<= 80 chars), '
    '"why_it_matters": 1-2 plain-language sentences}.'
)

_VALID_SEVERITY = {s.value for s in Severity}

# Heuristic base severity by change type, used when the LLM is unavailable.
_BASE_SEVERITY = {
    ChangeType.PRICE: Severity.MEDIUM,
    ChangeType.AVAILABILITY: Severity.MEDIUM,
    ChangeType.CLAUSE: Severity.HIGH,
    ChangeType.STATUS: Severity.HIGH,
    ChangeType.STRUCTURE: Severity.LOW,
    ChangeType.CONTENT: Severity.LOW,
    ChangeType.OTHER: Severity.LOW,
}


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip().strip("`").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return {}
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def _coerce_severity(value: object) -> str | None:
    if isinstance(value, str) and value.lower() in _VALID_SEVERITY:
        return value.lower()
    return None


def _heuristic(change: Change) -> tuple[str, str, str]:
    """Return (severity, headline, why_it_matters) without the LLM."""
    base = _BASE_SEVERITY.get(change.change_type, Severity.LOW)
    # Bump one level if the change looks highly significant.
    if (change.significance_score or 0) >= 0.8 and base == Severity.LOW:
        base = Severity.MEDIUM
    headline = f"{change.get_change_type_display()} change on {change.target.name}"
    why = change.summary or "A monitored change was detected on this page."
    return base, headline, why


def _llm_assess(change: Change) -> dict:
    from llm import client

    field_lines = "\n".join(
        f"- {c['field']}: {c.get('old')!r} -> {c.get('new')!r}" for c in (change.field_diffs or [])
    )
    user = (
        f"Target: {change.target.name} ({change.target.get_vertical_display()})\n"
        f"What the user watches: {change.target.watch_instructions or '(not specified)'}\n"
        f"Change type: {change.get_change_type_display()}\n"
        f"Structured field changes:\n{field_lines or '(none)'}\n\n"
        f"Text diff (truncated):\n{(change.text_diff or '')[:TEXT_DIFF_SNIPPET]}"
    )
    result = client.chat(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
        role="assess",
        operation="assess",
        target=change.target,
    )
    return _parse_json(result.text)


def assess_change(change: Change) -> Change:
    """Score severity + explain a meaningful change, then raise an Alert."""
    from llm import client

    severity = headline = why = None
    if client.is_configured():
        try:
            data = _llm_assess(change)
            severity = _coerce_severity(data.get("severity"))
            headline = (data.get("headline") or "").strip() or None
            why = (data.get("why_it_matters") or "").strip() or None
        except Exception:
            logger.exception("LLM assessment failed for change %s", change.pk)

    if severity is None or headline is None or why is None:
        h_sev, h_headline, h_why = _heuristic(change)
        severity = severity or h_sev
        headline = headline or h_headline
        why = why or h_why

    change.severity = severity
    change.why_it_matters = why
    change.save(update_fields=["severity", "why_it_matters", "updated_at"])

    Alert.objects.create(
        target=change.target,
        change=change,
        kind=AlertKind.CHANGE,
        level=severity,
        title=headline[:300],
        body=why,
    )
    return change
