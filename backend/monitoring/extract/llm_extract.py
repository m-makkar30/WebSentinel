"""LLM-assisted extraction into the target's typed schema (cheap extract model)."""

from __future__ import annotations

import json
import logging
import re

from llm import client

logger = logging.getLogger(__name__)

# Cap content sent to the model to control token spend (cost optimization).
CONTENT_LIMIT = 6000

_SYSTEM = (
    "You extract structured data from web page text. Respond with ONLY a single "
    "JSON object and nothing else — no prose, no code fences."
)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip().strip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return {}


def llm_extract(text: str, schema: dict[str, str], instructions: str = "", target=None) -> dict:
    """Ask the model for the schema fields as JSON. Returns a raw (un-coerced) dict."""
    fields_desc = "\n".join(f'- "{name}": {type_name}' for name, type_name in schema.items())
    user = (
        "Extract these fields (use null if absent; never invent values):\n"
        f"{fields_desc}\n\n"
        f"What the user cares about: {instructions or '(not specified)'}\n\n"
        f"PAGE CONTENT:\n{text[:CONTENT_LIMIT]}"
    )
    result = client.chat(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
        role="extract",
        operation="extract",
        target=target,
        max_tokens=512,
    )
    data = _parse_json(result.text)
    return data if isinstance(data, dict) else {}
