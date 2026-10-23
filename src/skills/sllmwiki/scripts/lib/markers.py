"""The two markers a narrative puts after what its sources don't say (design doc
§4.10): where they may go, their Terminology rows, and the move from the old ones.

A marker sits where a citation would: after the statement it covers, or at the
end of a heading, where it covers the whole section.
"""

import re

from . import numbering
from .citations import CITE
from .compat import mask_code_spans, mask_math_spans, scan

MARKERS = {
    '[→]': 'Our own reasoning, after a statement or on a section\'s heading: a conclusion, comparison or example no cited source states.',
    '[?]': 'A gap, after a statement or on a heading: something the question needs that the sources don\'t answer.',
}
OLD = {'[sllmwiki_reasoning]': '[→]', '[sllmwiki_gap]': '[?]'}
ASCII = {'[->]': '[→]'}  # the reasoning marker as typed without the arrow; finish-narrative writes the arrow
LEVEL_HINT = 4  # this many statement markers of a kind in one uncited section: mark its heading instead
_ANY = re.compile(r'\[→\](?!\()|\[\?\](?!\()')
_ASCII = re.compile(r'\[->\](?!\()')
_OLD = re.compile('|'.join(re.escape(m) for m in OLD))
_SENTENCE_END = re.compile(r'[.!?][)"”’*]*(?=\s|\Z)')
_HEADING = re.compile(r' {0,3}#{1,6}[ \t]')


def _masked(line):
    return mask_math_spans(mask_code_spans(line))


def uses(text):
    """[(line, column, marker)] for every marker in the narrative's prose, the Terminology table aside."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    span = numbering.section(text, 'Terminology')
    out = []
    for i, line in enumerate(lines):
        if kinds[i] == 'text' and not (span and span[0] <= i < span[1]):
            out += [(i, m.start(), m.group(0)) for m in _ANY.finditer(_masked(line))]
    return out


def unmark(title):
    """A heading's title without the marker at its end."""
    return re.sub(r'\s*(?:\[→\]|\[->\]|\[\?\])\s*\Z', '', title)


def defined(text):
    """The markers the Terminology table defines."""
    body = '\n'.join(_section_lines(text, 'Terminology'))
    return {m for m in MARKERS if f'**{m}**' in body}


def _section_lines(text, name):
    span = numbering.section(text, name)
    return text.split('\n')[span[0]:span[1]] if span else []


def check(text, on=True):
    """Findings (severity, code, line, message) about markers; on is Config.toml's markers setting."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    out = [('error', 'MARKER_OLD', i + 1, f'{m.group(0)} is the old marker: write {OLD[m.group(0)]} after the statement (finish-narrative.py converts it)')
           for i, line in enumerate(lines) if kinds[i] == 'text' for m in _OLD.finditer(_masked(line))]
    out += [('error', 'MARKER_OLD', i + 1, '[->] is written [→] (finish-narrative.py converts it)')
            for i, line in enumerate(lines) if kinds[i] == 'text' for _ in _ASCII.finditer(_masked(line))]
    used = uses(text)
    if not on:
        return out + [('error', 'MARKER_OFF', i + 1, f'{m}: Config.toml turns markers off; say it in words instead') for i, _, m in used]
    have = defined(text)
    statements = []
    for i, col, m in used:
        line = _masked(lines[i])
        before, after = line[:col], line[col + len(m):]
        if _HEADING.match(line):
            if after.strip():
                out.append(('error', 'MARKER_PLACEMENT', i + 1, f'{m} on a heading goes at its end, after the title'))
        elif not before.strip() or re.fullmatch(r'\s*(?:[-*+]|[0-9]+[.)]|>|\|)\s*', before) or not before.endswith(' ') \
                or re.match(r'\s*[a-z]', after):
            out.append(('error', 'MARKER_PLACEMENT', i + 1, f'{m} goes after the statement it covers, like a citation: "… statement. {m}"'))
        else:
            statements.append((i, m))
            if re.search(CITE.pattern + r'[ \t]*\Z', before) or re.match(r'\s*' + CITE.pattern, after):  # a citation sits where the marker does
                out.append(('error', 'MARKER_AND_CITATION', i + 1, f'a statement is cited or marked {m}, never both'))
        if m not in have:
            out.append(('error', 'MARKER_UNDEFINED', i + 1, f'{m} isn\'t defined in Terminology (finish-narrative.py adds it)'))
    return out + _level_hints(text, lines, statements)


def _level_hints(text, lines, statements):
    """A warning for a section whose statements are mostly marked one way and none cited: mark its heading instead."""
    heads = [h for h in numbering.headings(text) if h.level >= 2]
    out = []
    for j, h in enumerate(heads):
        end = heads[j + 1].line if j + 1 < len(heads) else len(lines)
        inside = [m for i, m in statements if h.line < i < end]
        cited = any(CITE.search(lines[i]) for i in range(h.line + 1, end))
        for m in MARKERS:
            if inside.count(m) >= LEVEL_HINT and not cited:
                out.append(('warning', 'MARKER_LEVEL', h.line + 1, f'"{unmark(h.title)}" marks {inside.count(m)} statements {m} and cites nothing: '
                                                                   f'mark its heading once instead'))
    return out


def migrate(text):
    """(text, markers converted): each old marker at a sentence's start becomes the new one after that sentence,
    [->] becomes [→], and old Terminology rows go, for add_rows to write the new ones."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    out, moved = [], 0
    for i, line in enumerate(lines):
        if kinds[i] == 'text' and _ASCII.search(_masked(line)):
            masked = _masked(line)
            spans = [m.span() for m in _ASCII.finditer(masked)]
            for a, b in reversed(spans):
                line = line[:a] + ASCII['[->]'] + line[b:]
            moved += len(spans)
        if kinds[i] != 'text' or not _OLD.search(line):
            out.append(line)
            continue
        if re.match(r'\s*\|\s*\*\*\[sllmwiki_', line):
            moved += 1
            continue
        while True:
            m = _OLD.search(_masked(line))
            if not m:
                break
            head, rest = line[:m.start()], line[m.end():].lstrip(' ')
            cell = re.search(r'(?<!\\)\|', rest) if line.lstrip().startswith('|') else None
            scope = rest[:cell.start()] if cell else rest
            end = _SENTENCE_END.search(_masked(scope))
            stop = end.end() if end else len(scope.rstrip())
            tail = rest[stop:]
            line = head + rest[:stop] + ' ' + OLD[m.group(0)] + (tail if not tail or tail[0] in ' |' else ' ' + tail)
            moved += 1
        out.append(line)
    return '\n'.join(out), moved


def add_rows(text):
    """(text, rows added): a Terminology row for each marker the narrative uses and doesn't define yet."""
    span = numbering.section(text, 'Terminology')
    need = [m for m in MARKERS if m in {u[2] for u in uses(text)} and m not in defined(text)]
    if not need or not span:
        return text, 0
    lines = text.split('\n')
    last_row = max((i for i in range(span[0], span[1]) if lines[i].lstrip().startswith('|')), default=None)
    rows = [f'| **{m}** | {MARKERS[m]} |' for m in need]
    if last_row is None:
        rows = ['| Term | Definition |', '|---|---|'] + rows
        at = span[0] + 1
        lines[at:at] = [''] + rows
    else:
        lines[last_row + 1:last_row + 1] = rows
    return '\n'.join(lines), len(need)
