"""Semantic change detection — the noise-suppressing detector.

Three signals, strongest first:

1. Structured field diff (extracted price/availability/clauses) — a change here
   is meaningful regardless of surrounding HTML noise.
2. Normalized-text comparison — volatile cosmetic content (dates, times, years,
   session/long ids) is stripped so rotating footers/timestamps collapse to
   identical. This makes suppression work even without an LLM, keeping the
   evaluation metric reproducible.
3. Embedding cosine similarity (pgvector) — when the LLM is configured, this
   suppresses reworded-but-same-meaning prose that text diffing would flag.
"""

from __future__ import annotations

import difflib
import logging
import math
import re
from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone

from ..models import Change, ChangeType, DetectionMethod, Snapshot, WatchTarget
from .naive import diff_text

logger = logging.getLogger(__name__)

# --- Normalization: remove volatile cosmetic content --------------------------
_MONTH = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_TIME = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:[ap]\.?m\.?)?\b", re.IGNORECASE)
_LONGNUM = re.compile(r"\b\d{6,}\b")
_HEX = re.compile(r"\b[0-9a-f]{16,}\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    t = text or ""
    for rx in (_MONTH, _DATE, _TIME, _LONGNUM, _HEX, _YEAR):
        t = rx.sub("", t)
    return _WS.sub(" ", t).strip()


def cosine(a: list[float] | None, b: list[float] | None) -> float | None:
    if not a or not b:
        return None
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return None
    return dot / (na * nb)


def diff_fields(old: dict | None, new: dict | None) -> list[dict]:
    old = old or {}
    new = new or {}
    changes = []
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            changes.append({"field": key, "old": old.get(key), "new": new.get(key)})
    return changes


def _infer_change_type(field_changes: list[dict]) -> str:
    names = " ".join(c["field"].lower() for c in field_changes)
    if any(k in names for k in ("price", "amount", "cost", "fee", "fare")):
        return ChangeType.PRICE
    if any(k in names for k in ("stock", "availab")):
        return ChangeType.AVAILABILITY
    if any(k in names for k in ("clause", "policy", "term", "privacy", "retention")):
        return ChangeType.CLAUSE
    return ChangeType.CONTENT


@dataclass
class SemanticResult:
    differs: bool
    meaningful: bool
    field_changes: list[dict] = field(default_factory=list)
    text_similarity: float = 1.0
    embedding_similarity: float | None = None
    change_type: str = ChangeType.CONTENT
    significance: float = 0.0
    summary: str = ""


def classify(
    prev_text: str,
    cur_text: str,
    prev_fields: dict | None,
    cur_fields: dict | None,
    *,
    prev_emb: list[float] | None = None,
    cur_emb: list[float] | None = None,
) -> SemanticResult:
    text_thresh = getattr(settings, "DIFF_TEXT_SIM_THRESHOLD", 0.92)
    emb_thresh = getattr(settings, "DIFF_EMBED_SIM_THRESHOLD", 0.97)

    field_changes = diff_fields(prev_fields, cur_fields)
    norm_prev, norm_cur = normalize(prev_text), normalize(cur_text)
    prose_differs = norm_prev != norm_cur
    differs = bool(field_changes) or prose_differs

    text_sim = (
        1.0 if not prose_differs else difflib.SequenceMatcher(None, norm_prev, norm_cur).ratio()
    )
    emb_sim = cosine(prev_emb, cur_emb)

    # Prose change is meaningful only if it changed substantially AND embeddings
    # (when available) don't say it means the same thing.
    prose_meaningful = (
        prose_differs and text_sim < text_thresh and (emb_sim is None or emb_sim < emb_thresh)
    )
    meaningful = bool(field_changes) or prose_meaningful

    if field_changes:
        parts = [f"{c['field']}: {c['old']!r} → {c['new']!r}" for c in field_changes[:5]]
        summary = "Field changes — " + "; ".join(parts)
        significance = min(1.0, 0.6 + 0.1 * len(field_changes))
    else:
        emb_note = f", embedding {emb_sim:.0%}" if emb_sim is not None else ""
        summary = f"Prose changed (text similarity {text_sim:.0%}{emb_note})"
        significance = round(1.0 - max(text_sim, emb_sim or 0.0), 4)

    return SemanticResult(
        differs=differs,
        meaningful=meaningful,
        field_changes=field_changes,
        text_similarity=round(text_sim, 4),
        embedding_similarity=None if emb_sim is None else round(emb_sim, 4),
        change_type=_infer_change_type(field_changes),
        significance=significance,
        summary=summary,
    )


def _embedding_for(snapshot: Snapshot) -> list[float] | None:
    """Return the snapshot's embedding, computing + caching it if the LLM is on."""
    if snapshot.embedding is not None:
        return list(snapshot.embedding)
    from llm import client as llm_client

    if not llm_client.is_configured() or not snapshot.content_text:
        return None
    try:
        limit = getattr(settings, "EMBED_CONTENT_LIMIT", 4000)
        vector = llm_client.embed([snapshot.content_text[:limit]])[0]
    except Exception:
        logger.exception("embedding failed for snapshot %s", snapshot.pk)
        return None
    snapshot.embedding = vector
    snapshot.save(update_fields=["embedding"])
    return vector


def semantic_detect(target: WatchTarget, current: Snapshot) -> Change | None:
    """Compare ``current`` to the prior snapshot; record a Change if it differs."""
    previous = (
        Snapshot.objects.filter(target=target, ok=True, id__lt=current.id)
        .order_by("-fetched_at")
        .first()
    )
    if previous is None:
        return None

    prev_emb = _embedding_for(previous)
    cur_emb = _embedding_for(current)

    result = classify(
        previous.content_text,
        current.content_text,
        previous.extracted,
        current.extracted,
        prev_emb=prev_emb,
        cur_emb=cur_emb,
    )
    if not result.differs:
        return None

    return Change.objects.create(
        target=target,
        previous_snapshot=previous,
        current_snapshot=current,
        detected_at=timezone.now(),
        detection_method=DetectionMethod.SEMANTIC,
        change_type=result.change_type,
        is_meaningful=result.meaningful,
        significance_score=result.significance,
        summary=result.summary,
        field_diffs=result.field_changes,
        text_diff=diff_text(previous.content_text, current.content_text).text_diff,
    )
