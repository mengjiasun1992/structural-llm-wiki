"""The owner's notes (design doc §4.10.1): the wiki owner's own view of a section,
agreed with them before it is written, kept apart from what the sources say and
from the narrative's own reasoning. Off unless Config.toml's owner_notes is true.

A note is a quote block at the end of a section's own text, after everything
else and before the next heading, its first line starting with the marker
[*<github username> <YYYY-MM-DD>]:

    > [\\*mengjiasun1992 2026-11-16] The whole network reads like if-blocks…

The * is written escaped, [\\*, so no renderer reads it as the start of
emphasis; finish-narrative escapes it. Several notes on one section are
separate quote blocks, newest first. A note holds the owner's words only: a
correction goes in a paragraph of its own, cited or marked, before the notes.
"""

import datetime
import re

from . import numbering
from .citations import CITE
from .compat import mask_spans, scan

TERM = '[\\*username date]'  # the Terminology row's term, as the markdown has it
DEFINITION = ('An owner\'s note: a quote block at the end of a section, the wiki owner\'s own view, agreed with them '
              'before it was written; the username and date say whose and when. Not a source.')
NO_NOTES = ('terminology', 'smes', 'references', 'metadata')  # sections that take no notes
_MARK = re.compile(r'\[(\\?)\*(?![*\]])([^\]\n]*)\](?!\()')  # [*…] or [\*…]; not [**bold**], [*] or a link's text
_USER_DATE = re.compile(r'([A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}) ([0-9]{4}-[0-9]{2}-[0-9]{2})\Z')
_LOOSE = re.compile(r'\S [0-9]{4}-[0-9]{1,2}-[0-9]{1,2}\Z')  # something, then a date: meant as a note's marker
_QUOTE = re.compile(r' {0,3}>[ \t]?')
_OTHER_MARKERS = re.compile(r'\[→\]|\[->\]|\[\?\]')


class Note:
    """One note: its marker's line and the last line of its quote block (0-based), whose and when."""

    def __init__(self, line, last, user, date, escaped):
        self.line, self.last, self.user, self.date, self.escaped = line, last, user, date, escaped


def _terminology(text):
    span = numbering.section(text, 'Terminology')
    return range(span[0], span[1]) if span else range(0)


def _marks(text):
    """[(line, column, match)] for every note marker, or attempt at one, in the prose, the Terminology table
    aside: a [*…] ending in a date, or one starting a quote block. Bracketed italics, [*sic*], are no marker."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    skip = _terminology(text)
    return [(i, m.start(), m) for i, line in enumerate(lines) if kinds[i] == 'text' and i not in skip
            for m in _MARK.finditer(mask_spans(line)) if _LOOSE.search(m.group(2)) or _starts_quote(line, m.start())]


def _valid_date(date):
    try:
        datetime.date.fromisoformat(date)
        return True
    except ValueError:
        return False


def _starts_quote(line, column):
    """Whether column is where a quote block's text starts on line."""
    m = _QUOTE.match(line)
    return bool(m) and column >= m.end() and not line[m.end():column].strip()


def _note_start(line):
    m = _MARK.search(mask_spans(line))
    return bool(m) and _starts_quote(line, m.start())


def notes(text):
    """Every well-formed note, in order."""
    lines = text.split('\n')
    out = []
    for i, col, m in _marks(text):
        um = _USER_DATE.match(m.group(2))
        if not (um and _valid_date(um.group(2)) and _starts_quote(lines[i], col)):
            continue
        last = i
        while last + 1 < len(lines) and _QUOTE.match(lines[last + 1]) and not _note_start(lines[last + 1]):
            last += 1
        out.append(Note(i, last, um.group(1), um.group(2), bool(m.group(1))))
    return out


def defined(text):
    """Whether Terminology has the notes' row."""
    lines = text.split('\n')
    return any(f'**{TERM}**' in lines[i] for i in _terminology(text))


def _section_title(head):
    title = re.sub(r'\s*(?:\[→\]|\[->\]|\[\?\])\s*\Z', '', head.title)
    return re.sub(r'\A[0-9]+(?:\.[0-9]+)*\.?\s+', '', title).strip().lower()


def check(text, on=False, names=None):
    """Findings (severity, code, line, message) about owner's notes; on is Config.toml's owner_notes.
    names: the lowercase titles of the sections that take no notes, in every language (default NO_NOTES)."""
    lines = text.split('\n')
    marks = _marks(text)
    if not on:
        return [('error', 'NOTE_OFF', i + 1, f'"{m.group(0)}": Config.toml\'s owner_notes is false; remove the note, or turn notes on')
                for i, _, m in marks]
    out = []
    for i, col, m in marks:
        um = _USER_DATE.match(m.group(2))
        if not um or not _valid_date(um.group(2)):
            out.append(('error', 'NOTE_FORMAT', i + 1, f'"{m.group(0)}": an owner\'s note starts [\\*<github username> <YYYY-MM-DD>]'))
        elif not _starts_quote(lines[i], col):
            out.append(('error', 'NOTE_INLINE', i + 1, f'"{m.group(0)}": a note is a quote block of its own, starting with its marker '
                                                       '(> [\\*user date] …), never inside a paragraph'))
        elif not m.group(1):
            out.append(('error', 'NOTE_ESCAPE', i + 1, f'"{m.group(0)}": write [\\* so no renderer reads * as emphasis '
                                                       '(sllmwiki finish-narrative does)'))
    found = notes(text)
    heads = numbering.headings(text)
    starts = {n.line: n for n in found}
    no_notes = names or set(NO_NOTES)
    by_section = {}
    for n in found:
        head = next((h for h in reversed(heads) if h.line < n.line), None)
        if head is None or head.level < 2 or _section_title(head) in no_notes:
            out.append(('error', 'NOTE_PLACEMENT', n.line + 1, 'a note goes at the end of a section\'s own text; '
                                                               'not in Terminology, SMEs, References or Metadata, or before the first section'))
            continue
        nxt = next((h.line for h in heads if h.line > n.line), len(lines))
        j = n.last + 1
        while j < nxt:
            if j in starts:
                j = starts[j].last + 1
            elif not lines[j].strip():
                j += 1
            else:
                out.append(('error', 'NOTE_PLACEMENT', n.line + 1, 'a note goes at the end of its section\'s own text, after everything else '
                                                                   'and before the next heading; a correction to it goes before the notes'))
                break
        body = '\n'.join(lines[n.line:n.last + 1])
        rest = mask_spans(body[body.index(']') + 1:])
        if CITE.search(rest) or _OTHER_MARKERS.search(rest):
            out.append(('error', 'NOTE_MIXED', n.line + 1, 'a note holds the owner\'s words only: put a citation or marker in a paragraph '
                                                           'of its own, before the notes'))
        by_section.setdefault(head.line, []).append(n)
    for group in by_section.values():
        for a, b in zip(group, group[1:]):
            if b.date > a.date:
                out.append(('error', 'NOTE_ORDER', b.line + 1, f'notes on one section go newest first: {b.date} comes after {a.date}'))
    if found and not defined(text):
        out.append(('error', 'NOTE_UNDEFINED', found[0].line + 1, f'{TERM} isn\'t defined in Terminology (sllmwiki finish-narrative adds it)'))
    return sorted(out, key=lambda f: f[2])


def escape(text):
    """(text, notes escaped): each note's [* written [\\*."""
    lines = text.split('\n')
    n = 0
    for note in notes(text):
        if not note.escaped:
            line = lines[note.line]
            at = line.index('[*')
            lines[note.line] = line[:at] + '[\\*' + line[at + 2:]
            n += 1
    return '\n'.join(lines), n


def without(text):
    """text with every note's lines blanked, the line count kept: what a word budget counts."""
    lines = text.split('\n')
    for note in notes(text):
        for j in range(note.line, note.last + 1):
            lines[j] = ''
    return '\n'.join(lines)


def add_row(text, pack=None):
    """(text, 1) with the notes' Terminology row added when the narrative has notes and no row yet, else (text, 0)."""
    t = pack.t if pack else (lambda s: s)
    span = numbering.section(text, 'Terminology')
    if not notes(text) or defined(text) or not span:
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
