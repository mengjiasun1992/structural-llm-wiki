"""Readers' annotations (design doc §4.10.1): a reader's own view of a section,
agreed with them before it is written, kept apart from what the sources say and
from the narrative's own reasoning. Off unless Config.toml's reader_annotations
is true.

An annotation is a quote block at the end of a section's own text, after
everything else and before the next heading, its first line starting with the
marker [* <YYYY-MM-DD> <github username>]:

    > [* 2026-11-16 mengjiasun1992] The whole network reads like if-blocks…

The space after * keeps every renderer from reading it as the start of
emphasis, so the marker is typed as it shows. Several annotations on one
section are separate quote blocks, newest first. An annotation states the
understanding the reader and the agent agreed on, corrections folded in, and
holds no citation or marker.
"""

import datetime
import re

from . import numbering
from .citations import CITE
from .compat import mask_spans, scan

TERM = '[\\* date username]'  # the Terminology row's term, its * escaped: inside **bold**, "**[* " would start emphasis
DEFINITION = ('A reader\'s annotation: a quote block at the end of a section, a reader\'s own view, agreed with them '
              'before it was written; the date and username say when and whose. Not a source.')
NO_ANNOTATIONS = ('terminology', 'smes', 'references', 'metadata')  # sections that take none
_MARK = re.compile(r'\[\*(?![*\]])([^\]\n]*)\](?!\()')  # [*…]; not [**bold**], [*] or a link's text
_DATE_USER = re.compile(r' ([0-9]{4}-[0-9]{2}-[0-9]{2}) ([A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38})\Z')
_LOOSE = re.compile(r'\A ?[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:\s|\Z)')  # a date first: meant as a marker
_QUOTE = re.compile(r' {0,3}>[ \t]?')
_OTHER_MARKERS = re.compile(r'\[→\]|\[->\]|\[\?\]')


class Annotation:
    """One annotation: its marker's line and the last line of its quote block (0-based), when and whose."""

    def __init__(self, line, last, date, user):
        self.line, self.last, self.date, self.user = line, last, date, user


def _terminology(text):
    span = numbering.section(text, 'Terminology')
    return range(span[0], span[1]) if span else range(0)


def _starts_quote(line, column):
    """Whether column is where a quote block's text starts on line."""
    m = _QUOTE.match(line)
    return bool(m) and column >= m.end() and not line[m.end():column].strip()


def _marks(text):
    """[(line, column, match)] for every marker, or attempt at one, in the prose, the Terminology table
    aside: a [*…] starting with a date, or one starting a quote block. Bracketed italics, [*sic*], are no marker."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    skip = _terminology(text)
    return [(i, m.start(), m) for i, line in enumerate(lines) if kinds[i] == 'text' and i not in skip
            for m in _MARK.finditer(mask_spans(line)) if _LOOSE.search(m.group(1)) or _starts_quote(line, m.start())]


def _valid_date(date):
    try:
        datetime.date.fromisoformat(date)
        return True
    except ValueError:
        return False


def _starts_annotation(line):
    m = _MARK.search(mask_spans(line))
    return bool(m) and _starts_quote(line, m.start())


def annotations(text):
    """Every well-formed annotation, in order."""
    lines = text.split('\n')
    out = []
    for i, col, m in _marks(text):
        dm = _DATE_USER.match(m.group(1))
        if not (dm and _valid_date(dm.group(1)) and _starts_quote(lines[i], col)):
            continue
        last = i
        while last + 1 < len(lines) and _QUOTE.match(lines[last + 1]) and not _starts_annotation(lines[last + 1]):
            last += 1
        out.append(Annotation(i, last, dm.group(1), dm.group(2)))
    return out


def defined(text):
    """Whether Terminology has the annotations' row."""
    lines = text.split('\n')
    return any(f'**{TERM}**' in lines[i] for i in _terminology(text))


def _section_title(head):
    title = re.sub(r'\s*(?:\[→\]|\[->\]|\[\?\])\s*\Z', '', head.title)
    return re.sub(r'\A[0-9]+(?:\.[0-9]+)*\.?\s+', '', title).strip().lower()


def check(text, on=False, names=None):
    """Findings (severity, code, line, message) about readers' annotations; on is Config.toml's reader_annotations.
    names: the lowercase titles of the sections that take none, in every language (default NO_ANNOTATIONS)."""
    lines = text.split('\n')
    marks = _marks(text)
    if not on:
        return [('error', 'ANNOTATION_OFF', i + 1, f'"{m.group(0)}": Config.toml\'s reader_annotations is false; '
                                                   'remove the annotation, or turn annotations on') for i, _, m in marks]
    out = []
    for i, col, m in marks:
        dm = _DATE_USER.match(m.group(1))
        if not dm or not _valid_date(dm.group(1)):
            out.append(('error', 'ANNOTATION_FORMAT', i + 1, f'"{m.group(0)}": an annotation starts [* <YYYY-MM-DD> <github username>]'))
        elif not _starts_quote(lines[i], col):
            out.append(('error', 'ANNOTATION_INLINE', i + 1, f'"{m.group(0)}": an annotation is a quote block of its own, starting with its '
                                                             'marker (> [* date username] …), never inside a paragraph'))
    found = annotations(text)
    heads = numbering.headings(text)
    starts = {a.line: a for a in found}
    none_here = names or set(NO_ANNOTATIONS)
    by_section = {}
    for a in found:
        head = next((h for h in reversed(heads) if h.line < a.line), None)
        if head is None or head.level < 2 or _section_title(head) in none_here:
            out.append(('error', 'ANNOTATION_PLACEMENT', a.line + 1, 'an annotation goes at the end of a section\'s own text; '
                                                                     'not in Terminology, SMEs, References or Metadata, or before the first section'))
            continue
        nxt = next((h.line for h in heads if h.line > a.line), len(lines))
        j = a.last + 1
        while j < nxt:
            if j in starts:
                j = starts[j].last + 1
            elif not lines[j].strip():
                j += 1
            else:
                out.append(('error', 'ANNOTATION_PLACEMENT', a.line + 1, 'an annotation goes at the end of its section\'s own text, after '
                                                                         'everything else and before the next heading'))
                break
        body = '\n'.join(lines[a.line:a.last + 1])
        rest = mask_spans(body[body.index(']') + 1:])
        if CITE.search(rest) or _OTHER_MARKERS.search(rest):
            out.append(('error', 'ANNOTATION_MIXED', a.line + 1, 'an annotation holds no citation or marker: put the claim in the '
                                                                 'section\'s text, cited or marked'))
        by_section.setdefault(head.line, []).append(a)
    for group in by_section.values():
        for a, b in zip(group, group[1:]):
            if b.date > a.date:
                out.append(('error', 'ANNOTATION_ORDER', b.line + 1, f'annotations on one section go newest first: {b.date} comes after {a.date}'))
    if found and not defined(text):
        out.append(('error', 'ANNOTATION_UNDEFINED', found[0].line + 1, f'{TERM} isn\'t defined in Terminology (sllmwiki finish-narrative adds it)'))
    return sorted(out, key=lambda f: f[2])


def without(text):
    """text with every annotation's lines blanked, the line count kept: what a word budget counts."""
    lines = text.split('\n')
    for a in annotations(text):
        for j in range(a.line, a.last + 1):
            lines[j] = ''
    return '\n'.join(lines)


def add_row(text, pack=None):
    """(text, 1) with the annotations' Terminology row added when the narrative has annotations and no row yet, else (text, 0)."""
    t = pack.t if pack else (lambda s: s)
    span = numbering.section(text, 'Terminology')
    if not annotations(text) or defined(text) or not span:
        return text, 0
    lines = text.split('\n')
    last_row = max((i for i in range(span[0], span[1]) if lines[i].lstrip().startswith('|')), default=None)
    row = f'| **{TERM}** | {t(DEFINITION)} |'
    if last_row is None:
        at = span[0] + 1
        lines[at:at] = ['', f'| {t("Term")} | {t("Definition")} |', '|---|---|', row]
    else:
        lines[last_row + 1:last_row + 1] = [row]
    return '\n'.join(lines), 1
