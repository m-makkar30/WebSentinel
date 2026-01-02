"""Extraction orchestration: rules first, LLM for what's left, then coerce."""

from __future__ import annotations

import logging

from llm import client as llm_client

from . import rules
from .schema import coerce

logger = logging.getLogger(__name__)

_EMPTY = (None, "", [], {})


def extract(snapshot) -> dict:
    """Populate ``snapshot.extracted`` per the target's schema and save it."""
    target = snapshot.target
    schema: dict[str, str] = target.extraction_schema or {}
    text = snapshot.content_text or ""
    if not schema:
        return {}

    # 1) Cheap deterministic rules.
    values = rules.rule_extract(text, schema)

    # 2) LLM only for fields the rules couldn't fill (and only if configured).
    missing = {f: t for f, t in schema.items() if values.get(f) in _EMPTY}
    if missing and llm_client.is_configured():
        try:
            from .llm_extract import llm_extract

            for field, value in llm_extract(
                text, missing, target.watch_instructions, target=target
            ).items():
                if field in schema:
                    values[field] = value
        except Exception:
            logger.exception("LLM extraction failed for target %s", target.pk)

    # 3) Coerce everything to its declared type.
    extracted = {field: coerce(values.get(field), type_name) for field, type_name in schema.items()}
    snapshot.extracted = extracted
    snapshot.save(update_fields=["extracted"])
    return extracted
