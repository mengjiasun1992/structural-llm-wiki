"""A narrative's citations: numbered links to a section of a saved source,
` [\\[3\\]](../sources/<slug>.md#<section>)`, each after a space, and the
Citations list that gives each number its target once (design doc §2, §4.5).

As in a paper, a reference sits inside its sentence, before the closing
punctuation, and several are separated by commas: "… exponentially [3], [6]."
The reasoning and gap markers ([→], [?]) take the same place. place() moves
references and markers written after the period, the earlier format, inside.
"""

import re

from . import numbering
from .compat import mask_code_spans, mask_math_spans, scan

CITE = re.compile(r'(?P<space>[ \t]?)\[\\\[(?P<n>[0-9]+)\\\]\]\((?P<target>[^)\s]+)\)')
_LISTED = re.compile(r'[ \t]*(?P<n>[0-9]+)\.[ \t]+.*?\]\((?P<target>[^)\s]+)\)')
_REF = r'(?:\[\\\[[0-9]+\\\]\]\([^)\s]+\)|\[→\]|\[\?\]|\[->\])'
# references (and markers) written after a sentence's closing punctuation: "… exponentially. [3] [6]"
_AFTER = re.compile(r'(?<=\S)(?P<punct>[.!?。！？])(?P<refs>(?:[ \t]+' + _REF + r')+)(?=[ \t]|\Z|[ \t]*\|)')
# two references side by side with no comma between them
_SIDE = re.compile(r'(?P<a>\[\\\[[0-9]+\\\]\]\([^)\s]+\))(?P<gap>[ \t]+)(?=\[\\\[[0-9]+\\\]\])')
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


def _prose_lines(text):
    """The indexes of the lines a reference may sit in: prose outside code, math, headings and the Citations list."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    span = _citations_span(text)
    return [i for i, line in enumerate(lines)
            if kinds[i] == 'text' and not (span and span[0] <= i < span[1]) and not re.match(r' {0,3}#', line)]


def _masked(line):
    return mask_math_spans(mask_code_spans(line))


def place(text):
    """(text, references moved): references and markers after a sentence's closing punctuation move
    inside it, and references side by side get a comma between them."""
    lines = text.split('\n')
    moved = 0
    for i in _prose_lines(text):
        line = lines[i]
        for m in reversed(list(_AFTER.finditer(_masked(line)))):
            refs = re.findall(_REF, line[m.start('refs'):m.end('refs')])
            line = line[:m.start('punct')] + ' ' + ', '.join(refs) + m.group('punct') + line[m.end('refs'):]
            moved += 1
        for m in reversed(list(_SIDE.finditer(_masked(line)))):
            line = line[:m.end('a')] + ',' + line[m.start('gap'):]
            moved += 1
        lines[i] = line
    return '\n'.join(lines), moved


def check_placement(text):
    """Findings for references written after the closing punctuation, or side by side without a comma."""
    lines = text.split('\n')
    out = []
    for i in _prose_lines(text):
        masked = _masked(lines[i])
        for _ in _AFTER.finditer(masked):
            out.append(('error', 'REFERENCE_PLACEMENT', i + 1, 'a reference goes inside its sentence, before the closing punctuation: '
                                                               '"… exponentially [3]." (finish-narrative.py moves it)'))
        for _ in _SIDE.finditer(masked):
            out.append(('error', 'REFERENCE_COMMA', i + 1, 'separate references with a comma: "[3], [6]" (finish-narrative.py adds it)'))
    return out


def check(text):
    """Findings (severity, code, line, message) for citations that don't match their list, or sit in the wrong place."""
    out = check_placement(text)
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
