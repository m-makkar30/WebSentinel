"""Naive change detection — the deliberate baseline.

This flags *any* textual difference between consecutive snapshots as a change,
with no noise suppression. It exists so the semantic detector (next commit) has
a baseline to measure false-positive reduction against. Keep it dumb on purpose.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from django.utils import timezone

from ..models import Change, ChangeType, DetectionMethod, Snapshot, WatchTarget

TEXT_DIFF_LIMIT = 20_000  # cap stored unified diff (chars)


@dataclass
class NaiveDiff:
    changed: bool
    similarity: float  # difflib ratio, 0..1
    added_lines: int
    removed_lines: int
    text_diff: str


def diff_text(old: str, new: str) -> NaiveDiff:
    old = old or ""
    new = new or ""
    old_lines = old.splitlines()
    new_lines = new.splitlines()

    unified = list(
        difflib.unified_diff(
            old_lines, new_lines, fromfile="previous", tofile="current", lineterm=""
        )
    )
    added = sum(1 for ln in unified if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in unified if ln.startswith("-") and not ln.startswith("---"))
    similarity = difflib.SequenceMatcher(None, old, new).ratio()

    return NaiveDiff(
        changed=old != new,
        similarity=similarity,
        added_lines=added,
        removed_lines=removed,
        text_diff="\n".join(unified)[:TEXT_DIFF_LIMIT],
    )


def detect_naive(target: WatchTarget, current: Snapshot) -> Change | None:
    """Compare ``current`` to the prior successful snapshot; record any diff."""
    previous = (
        Snapshot.objects.filter(target=target, ok=True, id__lt=current.id)
        .order_by("-fetched_at")
        .first()
    )
    if previous is None:
        return None  # first snapshot establishes the baseline

    result = diff_text(previous.content_text, current.content_text)
    if not result.changed:
        return None

    return Change.objects.create(
        target=target,
        previous_snapshot=previous,
        current_snapshot=current,
        detected_at=timezone.now(),
        detection_method=DetectionMethod.NAIVE,
        change_type=ChangeType.CONTENT,
        # The baseline has no notion of meaningfulness: everything "changed".
        is_meaningful=True,
        significance_score=round(1.0 - result.similarity, 4),
        summary=(
            f"Content changed: +{result.added_lines}/-{result.removed_lines} lines "
            f"(similarity {result.similarity:.0%})"
        ),
        text_diff=result.text_diff,
    )
