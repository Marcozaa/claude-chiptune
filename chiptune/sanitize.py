"""Make untrusted text (track metadata, lyrics) safe and tidy to print in a terminal.

Song titles and LRCLIB lyrics are user-submitted, so they may carry escape
sequences (clipboard writes, fake links, screen clears) or bidi overrides.
"""
from __future__ import annotations

import unicodedata

# Cc: C0/C1 controls incl. ESC/BEL, Cf: bidi + zero-width, Cs/Co: surrogates
# and private use, Zl/Zp: line/paragraph separators.
UNSAFE_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Zl", "Zp"})
ELLIPSIS = "…"


def clean(text: str) -> str:
    """Replace unsafe characters with spaces and collapse whitespace."""
    safe = "".join(" " if unicodedata.category(c) in UNSAFE_CATEGORIES else c for c in text)
    return " ".join(safe.split())


def _char_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def cell_width(text: str) -> int:
    """Terminal columns the text occupies (wide CJK = 2, combining marks = 0)."""
    return sum(_char_width(c) for c in text)


def truncate(text: str, limit: int) -> str:
    """Cut to at most `limit` terminal columns, ending with … when shortened."""
    if cell_width(text) <= limit:
        return text
    out, used = [], 0
    for ch in text:
        width = _char_width(ch)
        if used + width > limit - 1:
            break
        out.append(ch)
        used += width
    return "".join(out) + ELLIPSIS
