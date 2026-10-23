"""Headings: their levels, their numbers and their GitHub anchors.

A narrative numbers every heading of level 2 to 4 (design doc §4.5):
`## 3. Background`, `### 3.1 Why`, `#### 3.1.2 Detail`; the # title has no
number. Headings in code (lib/compat.py's scan) aren't headings.
"""

import re

from .compat import scan

_HEADING = re.compile(r' {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*\Z')
_NUMBER = re.compile(r'([0-9]+(?:\.[0-9]+)*)\.?[ \t]+')
NUMBERED = (2, 3, 4)


class Heading:
    """A heading: its line (0-based), level, number (or None), title without the
    number, and text, the heading as written (what GitHub's anchor comes from)."""

    def __init__(self, line, level, number, title, text=''):
        self.line, self.level, self.number, self.title, self.text = line, level, number, title, text or title


def split_number(text):
    """(number or None, title) of a heading's text: "5.1 Why" -> ("5.1", "Why")."""
    m = _NUMBER.match(text)
    return (m.group(1), text[m.end():]) if m else (None, text)


def headings(text):
    """Every ATX heading outside code, in order."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    out = []
    for i, line in enumerate(lines):
        m = _HEADING.match(line) if kinds[i] == 'text' else None
        if m:
            text = (m.group(2) or '').strip()
            number, title = split_number(text)
            out.append(Heading(i, len(m.group(1)), number, title.strip(), text))
    return out


def _expected(heads):
    """The number each numbered heading should carry, by its place in the structure."""
    counters = [0, 0, 0]
    out = {}
    for h in heads:
        if h.level not in NUMBERED:
            continue
        depth = h.level - 2
        counters[depth] += 1
        counters[depth + 1:] = [0] * (2 - depth)
        out[h.line] = '.'.join(str(c) for c in counters[:depth + 1])
    return out


def check(text):
    """Findings (severity, code, line, message) for headings whose number is missing or wrong."""
    out = []
    heads = headings(text)
    want = _expected(heads)
    for h in heads:
        if h.line not in want:
            continue
        if h.number is None:
            out.append(('error', 'HEADING_UNNUMBERED', h.line + 1, f'"{h.title}" needs its number, {want[h.line]} (--fix-numbering)'))
        elif h.number != want[h.line]:
            out.append(('error', 'HEADING_NUMBER', h.line + 1, f'"{h.number} {h.title}" should be numbered {want[h.line]} (--fix-numbering)'))
    return out


def renumber(text):
    """(text, headings changed) with every level 2-4 heading numbered by its place."""
    lines = text.split('\n')
    heads = headings(text)
    want = _expected(heads)
    changed = 0
    for h in heads:
        if h.line in want and h.number != want[h.line]:
            sep = '. ' if h.level == 2 else ' '
            lines[h.line] = f'{"#" * h.level} {want[h.line]}{sep}{h.title}'
            changed += 1
    return '\n'.join(lines), changed


def _plain(title):
    """A heading's text as GitHub renders it: links to their text, no code or emphasis marks."""
    title = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', title)
    title = title.replace('`', '')
    title = re.sub(r'(\*\*|__|\*|(?<!\w)_)(.+?)\1(?!\w)', r'\2', title)
    return re.sub(r'\\(.)', r'\1', title)


def anchor(text):
    """GitHub's anchor for a heading's full text (number included): lowercase,
    punctuation removed except - and _, spaces as -."""
    plain = _plain(text).strip().lower()
    return re.sub(r'[^\w\- ]', '', plain).replace(' ', '-')


def anchors(text):
    """{anchor: heading} for every heading; a repeated anchor gets -1, -2, as on GitHub."""
    out, seen = {}, {}
    for h in headings(text):
        base = anchor(h.text)
        n = seen.get(base, 0)
        seen[base] = n + 1
        out[base if n == 0 else f'{base}-{n}'] = h
    return out


def section(text, name):
    """(start, end) line span of the section whose anchor or unnumbered title is name
    (case-insensitive) or a language pack's translation of it, the heading included, up to the next heading of its level or
    higher; None when there is none."""
    heads = headings(text)
    lines = text.split('\n')
    by_anchor = anchors(text)
    target = by_anchor.get(name) or next((h for h in heads if h.title.lower() == name.lower()), None)
    if target is None:
        from . import language  # a section named in English is also found by a language pack's translation
        wanted = {n.lower() for n in language.names(name)[1:]}
        target = next((h for h in heads if h.title.lower() in wanted), None)
    if target is None:
        return None
    end = next((h.line for h in heads if h.line > target.line and h.level <= target.level), len(lines))
    return target.line, end
