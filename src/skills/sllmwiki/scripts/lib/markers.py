"""The two markers a narrative puts in front of what its sources don't say
(design doc §4.10): where they may go, and their Terminology rows."""

import re

from . import numbering
from .citations import CITE
from .compat import mask_code_spans, scan

MARKERS = {
    '[sllmwiki_reasoning]': 'The narrative\'s own reasoning: a conclusion, comparison or reconstruction no cited source states.',
    '[sllmwiki_gap]': 'Something the question needs that the sources don\'t answer.',
}
_ANY = re.compile('|'.join(re.escape(m) for m in MARKERS))
_SENTENCE_END = re.compile(r'[.!?](?=\s|\Z)')
_BEFORE_OK = re.compile(r'(?:\A|[.!?:|]|^[ \t]*(?:[-*+]|[0-9]+[.)]|>))[ \t]*\Z')


def uses(text):
    """[(line, column, marker)] for every marker in the narrative's prose."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    out = []
    for i, line in enumerate(lines):
        if kinds[i] == 'text':
            masked = mask_code_spans(line)
            out += [(i, m.start(), m.group(0)) for m in _ANY.finditer(masked)]
    return out


def defined(text):
    """The markers the Terminology table defines."""
    body = '\n'.join(_section_lines(text, 'Terminology'))
    return {m for m in MARKERS if m in body}


def _section_lines(text, name):
    span = numbering.section(text, name)
    return text.split('\n')[span[0]:span[1]] if span else []


def check(text, on=True):
    """Findings (severity, code, line, message) about markers; on is Config.toml's markers setting."""
    lines = text.split('\n')
    span = numbering.section(text, 'Terminology')
    out = []
    used = [(i, col, m) for i, col, m in uses(text) if not (span and span[0] <= i < span[1])]
    if not on:
        return [('error', 'MARKER_OFF', i + 1, f'{m}: Config.toml turns markers off; say it in words instead') for i, _, m in used]
    have = defined(text)
    for i, col, m in used:
        before = mask_code_spans(lines[i])[:col]
        if not _BEFORE_OK.search(before) and not re.search(CITE.pattern + r'[ \t]*\Z', before):  # after a citation is a sentence start
            out.append(('error', 'MARKER_PLACEMENT', i + 1, f'{m} goes at the start of the sentence it covers'))
        rest = lines[i][col + len(m):]
        end = _SENTENCE_END.search(rest)
        sentence, after = (rest[:end.end()], rest[end.end():]) if end else (rest, '')
        if CITE.search(sentence) or re.match(r'\s*' + CITE.pattern, after):  # a citation follows its sentence's period
            out.append(('error', 'MARKER_AND_CITATION', i + 1, f'a sentence is cited or marked {m}, never both'))
        if m not in have:
            out.append(('error', 'MARKER_UNDEFINED', i + 1, f'{m} isn\'t defined in Terminology (finish-narrative.py adds it)'))
    return out


def add_rows(text):
    """(text, rows added): a Terminology row for each marker the narrative uses and doesn't define yet."""
    span = numbering.section(text, 'Terminology')
    need = [m for m in MARKERS if m in {u[2] for u in uses(text) if not (span and span[0] <= u[0] < span[1])} and m not in defined(text)]
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
