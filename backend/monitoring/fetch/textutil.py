"""HTML -> readable text, and content hashing for skip-unchanged/diffing."""

from __future__ import annotations

import hashlib
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# We deliberately use the html.parser on feeds too (no lxml dependency); it
# extracts their text fine. Silence bs4's "this looks like XML" advisory.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_DROP_TAGS = ("script", "style", "noscript", "template", "svg")


def html_to_text(html: str) -> str:
    """Strip markup/boilerplate tags and return normalized visible text."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(_DROP_TAGS):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()
