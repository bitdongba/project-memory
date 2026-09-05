"""Small shared Markdown destination parser for validation and index routing.

This covers inline links/images and reference definitions, not full Markdown
rendering. Returned offsets refer to the original text for stable diagnostics.
"""

from __future__ import annotations

import re
import string
from typing import Iterable, Optional, Tuple


INLINE_START_RE = re.compile(r"!?\[(?:\\.|[^\]\\\n])*\]\(")
REFERENCE_START_RE = re.compile(r"^ {0,3}\[(?:\\.|[^\]\\\n])+\]:[ \t]*", re.MULTILINE)
ESCAPABLE = frozenset(string.punctuation)
ESCAPE_RE = re.compile(r"\\([" + re.escape(string.punctuation) + r"])")


def unescape_destination(raw: str) -> str:
    """Remove angle delimiters and CommonMark ASCII-punctuation escapes."""

    value = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
    return ESCAPE_RE.sub(r"\1", value)


def _destination_end(text: str, start: int) -> Optional[int]:
    angle = start < len(text) and text[start] == "<"
    depth = 0
    index = start + 1 if angle else start
    while index < len(text):
        character = text[index]
        if character == "\\" and index + 1 < len(text) and text[index + 1] in ESCAPABLE:
            index += 2
            continue
        if angle:
            if character == ">":
                return index + 1
            if character in "<\r\n":
                return None
        else:
            if character.isspace() or ord(character) < 32:
                break
            if character == "(":
                depth += 1
            elif character == ")":
                if depth == 0:
                    break
                depth -= 1
        index += 1
    return None if angle or depth else index


def parse_inline_link(text: str, start: int = 0) -> Optional[Tuple[str, int, int]]:
    """Return (raw destination, destination offset, end of link), if complete."""

    prefix = INLINE_START_RE.match(text, start)
    if prefix is None:
        return None
    target_start = prefix.end()
    while target_start < len(text) and text[target_start].isspace():
        target_start += 1
    target_end = _destination_end(text, target_start)
    if target_end is None:
        return None
    index = target_end
    while index < len(text) and text[index].isspace():
        index += 1
    # An optional title requires whitespace after the destination.
    if index > target_end and index < len(text) and text[index] in "\"'(":
        closing = ")" if text[index] == "(" else text[index]
        index += 1
        while index < len(text) and text[index] != closing:
            if text[index] == "\\" and index + 1 < len(text) and text[index + 1] in ESCAPABLE:
                index += 2
            else:
                index += 1
        if index == len(text):
            return None
        index += 1
        while index < len(text) and text[index].isspace():
            index += 1
    if index >= len(text) or text[index] != ")":
        return None
    return text[target_start:target_end], target_start, index + 1


def iter_link_destinations(text: str) -> Iterable[Tuple[str, int]]:
    """Yield raw destinations and offsets from inline and reference links."""

    for match in INLINE_START_RE.finditer(text):
        parsed = parse_inline_link(text, match.start())
        if parsed is not None:
            raw, start, _ = parsed
            yield raw, start
    for match in REFERENCE_START_RE.finditer(text):
        start = match.end()
        end = _destination_end(text, start)
        if end is not None and end > start:
            yield text[start:end], start
