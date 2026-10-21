"""A narrative's title, Abstract and Metadata section (design doc §4.5).

    ## 9. Metadata

    - **Version:** 1.1
    - **Template:** technical_brief_overview
    - **Created:** 2026-10-01
    - **Last modified:** 2026-10-21
    - **History:**
      - 1.1 (2026-10-21): Added the retry budget.
      - 1.0 (2026-10-01): First version.
"""

import re

from . import numbering

FIELDS = (('version', 'Version'), ('template', 'Template'), ('created', 'Created'), ('last_modified', 'Last modified'))
_FIELD = re.compile(r'- \*\*(?P<name>[^*]+):\*\*[ \t]*(?P<value>.*)\Z')
_ENTRY = re.compile(r'[ \t]+- (?P<version>[0-9]+\.[0-9]+) \((?P<date>[0-9-]+)\): (?P<note>.*)\Z')


def title(text):
    """The question: the narrative's # title."""
    m = re.search(r'^# (.+?)[ \t]*$', text, re.M)
    return m.group(1) if m else None


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
    """{version, template, created, last_modified, history: [(version, date, note)]}; absent fields are None."""
    out = {key: None for key, _ in FIELDS}
    out['history'] = []
    names = {label.lower(): key for key, label in FIELDS}
    for line in section_lines(text, 'Metadata'):
        m = _FIELD.match(line.strip()) if line.startswith('-') else None
        if m and m.group('name').lower() in names:
            out[names[m.group('name').lower()]] = m.group('value').strip() or None
        e = _ENTRY.match(line)
        if e:
            out['history'].append((e.group('version'), e.group('date'), e.group('note')))
    return out


def bump(version, kind):
    """The next version: minor 1.1 -> 1.2, major 1.1 -> 2.0; a narrative's first version is 1.0."""
    if not version:
        return '1.0'
    major, minor = (int(p) for p in version.split('.'))
    return f'{major + 1}.0' if kind == 'major' else f'{major}.{minor + 1}'


def write(text, fields, history=None):
    """text with the Metadata fields set (and a history entry (version, date, note)
    added at the top), in the field order above; other lines kept."""
    span = numbering.section(text, 'Metadata')
    if not span:
        raise ValueError('the narrative has no Metadata section')
    lines = text.split('\n')
    body = lines[span[0] + 1:span[1]]
    current = read(text)
    current.update({k: v for k, v in fields.items() if v is not None})
    entries = ([history] if history else []) + current['history']
    known = {label.lower() for _, label in FIELDS} | {'history'}
    other = [line for line in body if line.strip() and not _ENTRY.match(line)
             and not (_FIELD.match(line.strip()) and _FIELD.match(line.strip()).group('name').lower() in known)]
    block = [f'- **{label}:** {current[key]}' for key, label in FIELDS if current[key]]
    if entries:
        block.append('- **History:**')
        block += [f'  - {v} ({d}): {n}' for v, d, n in entries]
    new = [''] + block + ([''] + other if other else []) + ['']
    return '\n'.join(lines[:span[0] + 1] + new + lines[span[1]:])
