"""A narrative's title, Abstract and Metadata section (design doc §4.5).

    ## 9. Metadata

    - **Version:** 1.1
    - **Template:** technical_brief_overview
    - **Language:** en
    - **Model:** claude-opus-5-5
    - **Created:** 2026-10-01
    - **Last modified:** 2026-10-21
    - **Words:** 1,240 (about 5 min)
    - **History:**
      - 1.1 (2026-10-21): Added the retry budget.
      - 1.0 (2026-10-01): First version.
    - **Reading plan:**
      1. `retry-blog`, in full: medium relevance, authority C, 2025-02-01
      2. `gateway-design-doc`, in full: high relevance, authority A, 2026-09-30

The model and the reading plan are views of the narrative's manifest entry
(its models and grades), and the words a count of its text (reading()), all
written by finish-narrative. So is a reading-time line under the title
(*About 5 min read.*, in the narrative's language), when the narrative has one:
the writer adds it where the wiki's audience wants it, and finish-narrative keeps
its minutes those of Words (with_reading_line). That line also ends with a generated
pointer to the narrative's prerequisites, *Read first: …*, when it has some
(lib/prerequisites.py), on a line of its own without a reading time.
"""

import re

from . import numbering

FIELDS = (('version', 'Version'), ('template', 'Template'), ('language', 'Language'), ('model', 'Model'), ('created', 'Created'), ('last_modified', 'Last modified'),
          ('words', 'Words'))
WORDS_PER_MINUTE = 230  # a reader's pace through technical prose; CJK text counts its characters as words (lib/language.py)
UNREAD = ('References', 'SMEs', 'Metadata')  # sections a reader looks things up in rather than reads
_FIELD = re.compile(r'- \*\*(?P<name>[^*]+):\*\*[ \t]*(?P<value>.*)\Z')
_ENTRY = re.compile(r'[ \t]+- v?(?P<version>[0-9]+\.[0-9]+) \((?P<date>[0-9-]+)\): (?P<note>.*)\Z')  # v1.0: the earlier form
_STEP = re.compile(r'[ \t]+[0-9]+\. (?P<step>.*)\Z')


def title(text):
    """The question: the narrative's # title."""
    m = re.search(r'^# (.+?)[ \t]*$', text, re.M)
    return m.group(1) if m else None


READING_LINE = 'About {n} min read.'  # the reading-time line's words, translated by the language packs
READ_FIRST = 'Read first: {links} ({section}).'  # its generated pointer to the prerequisites (lib/prerequisites.py)
REGION_START = '<!-- sllmwiki:reading-order'  # how the generated Before you read / Where to go next region starts
REGION_END = '<!-- /sllmwiki:reading-order -->'


def _pattern(wording, holes):
    out = re.escape(wording)
    for hole, pattern in holes.items():
        out = out.replace(re.escape(hole), pattern)
    return out


def _is_read_first(rest):
    from .language import names
    return any(re.fullmatch(_pattern(w, {'{links}': '.+', '{section}': '.+'}), rest) for w in names(READ_FIRST))


def _reading_line(lines):
    """(index, wording, minutes, read_first) of the line under the # title, past blank lines: *<READING_LINE or a
    pack's translation of it>*, then the generated *Read first* sentence when the narrative has prerequisites,
    each optional; None without one. wording keeps {n} for the minutes; minutes is that part as written."""
    from .language import names
    start = next((i + 1 for i, line in enumerate(lines) if line.startswith('# ')), None)
    i = next((j for j in range(start, len(lines)) if lines[j].strip()), None) if start is not None else None
    m = re.fullmatch(r'\*(?P<body>[^*].*?)\*[ \t]*', lines[i]) if i is not None else None
    if not m:
        return None
    body = m.group('body')
    for wording in names(READING_LINE):
        t = re.match(_pattern(wording, {'{n}': '[0-9]+'}), body)
        if t:
            rest = body[t.end():].strip()
            if not rest or _is_read_first(rest):
                return i, wording, t.group(0), rest
    return (i, None, '', body.strip()) if _is_read_first(body.strip()) else None


def _line(minutes, first):
    return '*' + ' '.join(p for p in (minutes, first) if p) + '*'


def without_reading_line(text):
    """text without its reading-time line (and the blank line after it), for the book, whose version line shows it."""
    lines = text.split('\n')
    found = _reading_line(lines)
    if not found:
        return text
    del lines[found[0]:found[0] + (2 if found[0] + 1 < len(lines) and not lines[found[0] + 1].strip() else 1)]
    return '\n'.join(lines)


def with_reading_line(text):
    """text with its reading-time line, when it has one, giving reading()'s minutes; unchanged without one."""
    lines = text.split('\n')
    found = _reading_line(lines)
    if not found or not found[1]:
        return text
    i, wording, _, first = found
    lines[i] = _line(wording.replace('{n}', str(reading(text)[1])), first)
    return '\n'.join(lines)


def read_first(text):
    """The generated Read first sentence of the line under the title, or ''."""
    found = _reading_line(text.split('\n'))
    return found[3] if found else ''


def with_read_first(text, sentence):
    """text whose line under the title ends with sentence (the generated Read first pointer), or without one when
    sentence is empty: added after the minutes, or as a line of its own under the title, which goes when it's empty."""
    lines = text.split('\n')
    found = _reading_line(lines)
    if found:
        i, wording, minutes, _ = found
        if minutes or sentence:
            lines[i] = _line(minutes, sentence)
        else:
            del lines[i:i + (2 if i + 1 < len(lines) and not lines[i + 1].strip() else 1)]
        return '\n'.join(lines)
    title = next((i for i, line in enumerate(lines) if line.startswith('# ')), None)
    if not sentence or title is None:
        return text
    lines[title + 1:title + 1] = ['', _line('', sentence)]
    if title + 3 < len(lines) and lines[title + 3].strip():
        lines.insert(title + 3, '')
    return '\n'.join(lines)


def without_generated(text):
    """text without what lib/prerequisites.py writes: the reading-order region in the Appendix and the Read first
    sentence under the title. It's derived from other narratives, so it counts neither as words nor as a change."""
    lines = text.split('\n')
    found = _reading_line(lines)
    if found and found[3]:
        if found[2]:
            lines[found[0]] = _line(found[2], '')
        else:
            del lines[found[0]]
    out, inside, took = [], False, False
    for line in lines:
        if line.startswith(REGION_START):
            inside = took = True
        if not inside:
            out.append(line)
        if line.strip() == REGION_END:
            inside = False
    if took:  # an Appendix that held only the region was made for it
        from .language import names
        heads = [h for h in numbering.headings('\n'.join(out)) if h.level <= 2]
        for j, h in enumerate(heads):
            end = heads[j + 1].line if j + 1 < len(heads) else len(out)
            if h.level == 2 and h.title.lower() in {n.lower() for n in names('Appendix')} and not any(x.strip() for x in out[h.line + 1:end]):
                del out[h.line:end]
                break
    return '\n'.join(out)


def reading(text):
    """(words, minutes) of what a reader reads in the narrative: everything but its front matter, code and
    diagram blocks, its reading-time line, what lib/prerequisites.py generates, and the References, SMEs and Metadata sections; at WORDS_PER_MINUTE,
    at least a minute."""
    from .compat import scan
    from .narrativecheck import words  # the count budgets use: markdown, link targets and code fences left out
    lines = text.split('\n')
    found = _reading_line(lines)
    if found:
        del lines[found[0]]
    lines = without_generated('\n'.join(lines)).split('\n')
    for name in UNREAD:
        span = numbering.section('\n'.join(lines), name)
        if span:
            del lines[span[0]:span[1]]
    kinds, _ = scan(lines)
    n = words([line for line, kind in zip(lines, kinds) if kind in ('text', 'math')])
    return n, max(1, round(n / WORDS_PER_MINUTE))


def reading_label(text):
    """Metadata's Words: '1,240 (about 5 min)'."""
    n, minutes = reading(text)
    return f'{n:,} (about {minutes} min)'


def section_lines(text, name):
    """The lines of the section titled name, without its heading; [] without one."""
    span = numbering.section(text, name)
    return text.split('\n')[span[0] + 1:span[1]] if span else []


def abstract(text):
    """The Abstract's text, its paragraphs joined by a blank line."""
    paras, cur = [], []
    for line in section_lines(text, 'Abstract') + ['']:
        if line.strip():
            cur.append(line.strip())
        elif cur:
            paras.append(' '.join(cur))
            cur = []
    return '\n\n'.join(paras)


def read(text):
    """{version, template, model, created, last_modified, history: [(version, date, note)],
    plan: [step]}; absent fields are None."""
    out = {key: None for key, _ in FIELDS}
    out['history'], out['plan'] = [], []
    names = {label.lower(): key for key, label in FIELDS}
    for line in section_lines(text, 'Metadata'):
        m = _FIELD.match(line.strip()) if line.startswith('-') else None
        if m and m.group('name').lower() in names:
            out[names[m.group('name').lower()]] = m.group('value').strip() or None
        e = _ENTRY.match(line)
        if e:
            out['history'].append((e.group('version'), e.group('date'), e.group('note')))
        s = _STEP.match(line)
        if s:
            out['plan'].append(s.group('step'))
    return out


def bump(version, kind):
    """The next version: minor 1.1 -> 1.2, major 1.1 -> 2.0; a narrative's first version is 1.0."""
    if not version:
        return '1.0'
    major, minor = (int(p) for p in version.split('.'))
    return f'{major + 1}.0' if kind == 'major' else f'{major}.{minor + 1}'


def write(text, fields, history=None, plan=None):
    """text with the Metadata fields set (and a history entry (version, date, note)
    added at the top, and the reading plan's steps replaced when plan is given), in
    the order above; other lines kept."""
    span = numbering.section(text, 'Metadata')
    if not span:
        raise ValueError('the narrative has no Metadata section')
    lines = text.split('\n')
    body = lines[span[0] + 1:span[1]]
    current = read(text)
    current.update({k: v for k, v in fields.items() if v is not None})
    entries, seen = [], set()
    for entry in ([history] if history else []) + current['history']:
        if entry[0] not in seen:  # one entry per version: an old v1.0 line and its 1.0 copy are the same
            seen.add(entry[0])
            entries.append(entry)
    entries.sort(key=lambda e: tuple(int(p) for p in e[0].split('.')), reverse=True)  # newest first
    steps = current['plan'] if plan is None else plan
    known = {label.lower() for _, label in FIELDS} | {'history', 'reading plan'}
    other = [line for line in body if line.strip() and not _ENTRY.match(line) and not _STEP.match(line)
             and not (_FIELD.match(line.strip()) and _FIELD.match(line.strip()).group('name').lower() in known)]
    block = [f'- **{label}:** {current[key]}' for key, label in FIELDS if current[key]]
    if entries:
        block.append('- **History:**')
        block += [f'  - {v} ({d}): {n}' for v, d, n in entries]
    if steps:
        block.append('- **Reading plan:**')
        block += [f'  {i}. {s}' for i, s in enumerate(steps, 1)]
    new = [''] + block + ([''] + other if other else []) + ['']
    return '\n'.join(lines[:span[0] + 1] + new + lines[span[1]:])
