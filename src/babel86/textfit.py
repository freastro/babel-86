"""Fit text into a box: wrap, keep the newest lines, and ellipsise. No Tk dependency.

Everything takes a `measure(str) -> float` callable so it can be tested without a display.
Text is split on spaces first, then, for long unspaced runs such as Khmer or CJK, on
grapheme-like clusters so combining marks and joiners never get separated from their base.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable

Measure = Callable[[str], float]

# Characters that bind the following character to the preceding cluster.
_JOINERS = {
    "\u200d",  # zero width joiner
    "\u17d2",  # Khmer coeng (subscript consonant marker)
    "\u094d",  # Devanagari virama
}
ELLIPSIS = "\u2026"


def clusters(text: str) -> list[str]:
    """Split text into units that must not be broken apart when wrapping mid-word."""
    out: list[str] = []
    for ch in text:
        glued = unicodedata.category(ch) in ("Mn", "Mc", "Me") or ch in _JOINERS or ch == "\u200c"
        if out and (glued or out[-1][-1] in _JOINERS):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def wrap(text: str, measure: Measure, max_width: float) -> list[str]:
    """Greedy word wrap; words wider than the box are split by cluster."""
    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = word if not current else f"{current} {word}"
        if measure(candidate) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if measure(word) <= max_width:
            current = word
            continue
        for unit in clusters(word):
            if current and measure(current + unit) > max_width:
                lines.append(current)
                current = unit
            else:
                current += unit
    if current or not lines:
        lines.append(current)
    return lines


def newest_lines(text: str, measure: Measure, max_width: float, max_lines: int = 2) -> list[str]:
    """Wrap text and keep the last `max_lines` lines, trimming from the start with an ellipsis."""
    if not text:
        return []
    lines = wrap(text, measure, max_width)
    if len(lines) <= max_lines:
        return lines
    kept = lines[-max_lines:]
    head = clusters(kept[0])
    while head and measure(ELLIPSIS + "".join(head)) > max_width:
        head.pop(0)
    kept[0] = ELLIPSIS + "".join(head)
    return kept


def ellipsize(text: str, measure: Measure, max_width: float) -> str:
    """Trim the end of one line so it fits, ending with an ellipsis."""
    if measure(text) <= max_width:
        return text
    units = clusters(text)
    while units and measure("".join(units) + ELLIPSIS) > max_width:
        units.pop()
    return "".join(units) + ELLIPSIS
