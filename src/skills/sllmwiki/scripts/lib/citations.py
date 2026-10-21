"""A narrative's citations: numbered links to a section of a saved source,
` [\\[3\\]](../sources/<slug>.md#<section>)`, each after a space, and the
Citations list that gives each number its target once (design doc §2, §4.5)."""

import re

from . import numbering
from .compat import scan

CITE = re.compile(r'(?P<space>[ \t]?)\[\\\[(?P<n>[0-9]+)\\\]\]\((?P<target>[^)\s]+)\)')
_LISTED = re.compile(r'[ \t]*(?P<n>[0-9]+)\.[ \t]+.*?\]\((?P<target>[^)\s]+)\)')
SOURCE_TARGET = re.compile(r'\.\./sources/(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.md(?:#(?P<anchor>[^)\s]+))?\Z')


class Cite:
    def __init__(self, line, n, target, spaced):
        self.line, self.n, self.target, self.spaced = line, n, target, spaced

    @property
    def slug(self):
        m = SOURCE_TARGET.match(self.target)
        return m.group('slug') if m else None


def _citations_span(text):
    return numbering.section(text, 'Citations')


def cites(text):
    """Every citation in the narrative outside code and the Citations list."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    span = _citations_span(text)
    out = []
    for i, line in enumerate(lines):
        if kinds[i] != 'text' or (span and span[0] <= i < span[1]):
            continue
        for m in CITE.finditer(line):
            out.append(Cite(i, int(m.group('n')), m.group('target'), bool(m.group('space')) or m.start() == 0))
    return out


def listed(text):
    """{n: (line, target)} from the Citations list."""
    span = _citations_span(text)
    if not span:
        return {}
    lines = text.split('\n')
    out = {}
    for i in range(span[0] + 1, span[1]):
        m = _LISTED.match(lines[i])
        if m:
            out.setdefault(int(m.group('n')), (i, m.group('target')))
    return out


def check(text):
    """Findings (severity, code, line, message) for citations that don't match their list."""
    out = []
    used = cites(text)
    listing = listed(text)
    first = []
    for c in used:
        if not c.spaced:
            out.append(('error', 'CITATION_SPACE', c.line + 1, f'[{c.n}] needs a space before it'))
        if not SOURCE_TARGET.match(c.target):
            out.append(('error', 'CITATION_TARGET', c.line + 1, f'[{c.n}] must point at a saved source\'s section, ../sources/<slug>.md#<section>, not {c.target}'))
        if c.n not in listing:
            out.append(('error', 'CITATION_UNLISTED', c.line + 1, f'[{c.n}] isn\'t in the Citations list'))
        elif listing[c.n][1] != c.target:
            out.append(('error', 'CITATION_MISMATCH', c.line + 1, f'[{c.n}] points at {c.target}, but the Citations list gives {listing[c.n][1]}'))
        if c.n not in first:
            first.append(c.n)
    if first != sorted(first) or (first and first != list(range(1, len(first) + 1))):
        out.append(('error', 'CITATION_ORDER', used[0].line + 1, f'citations are numbered 1, 2, 3... in order of first use; found {first}'))
    for n, (line, _) in sorted(listing.items()):
        if n not in first:
            out.append(('warning', 'CITATION_UNUSED', line + 1, f'[{n}] is listed but never cited'))
    return out
