"""The wiki's shared language (design doc §4.5): each narrative's ID, the terms it
defines, the terms it borrows from another narrative, and its links into others.

A term is defined once, in the Terminology or Glossary of the narrative whose
subject it belongs to. Another narrative that uses it borrows it: its row ends
"From [<id>](<that narrative>.md#<section>)." and finish-narrative fills in the
owner's definition, word for word, so the wiki describes a thing one way.

  narrative_id(text)                 the ID in the Metadata, or None
  suggest_id(slug)                   a starting point for a new narrative's ID
  terms(text)                        [Term] in its Terminology and Glossary tables
  sync(root, text, own_slug)         (text, rows filled, problems): borrowed rows from their owners
  check_one(root, rel, text)         a narrative's findings: NO_ID, BAD_ID, TERM_OWNER, NARRATIVE_ANCHOR
  repair_links(root, rel, text)      (text, links fixed): links to a section of another narrative that moved
  check(root, fix)                   the wiki's findings: NARRATIVE_ID_*, TERM_DEFINED_TWICE, TERM_DRIFT,
                                     NARRATIVE_ANCHOR (with fix, repaired)
  render(root)                       the generated terms page
"""

import os
import re

from . import layout, manifest, metadata, numbering
from .compat import escape, scan
from .util import read_text, write_text

ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
MAX_ID = 40
SECTIONS = ('Terminology', 'Glossary')
GENERATED = '<!-- sllmwiki:generated: rewritten by wiki-check.py --fix -->'
_ROW = re.compile(r'\s*\|\s*\*\*(?P<term>.+?)\*\*\s*\|\s*(?P<definition>.*?)\s*\|\s*\Z')
_FROM = re.compile(r'(?P<text>.*?)\s*From \[(?P<id>[^\]]+)\]\((?P<target>[^)\s]+)\)\.?\Z')
_LINK = re.compile(r'\]\((?P<file>[^)\s#]+\.md)#(?P<anchor>[^)\s]+)\)')
_QUESTION_WORDS = {'what', 'is', 'are', 'a', 'an', 'the', 'how', 'does', 'do', 'when', 'should', 'why', 'which', 'it', 'work',
                   'and', 'of', 'for', 'to', 'in', 'on', 'can', 'i', 'we', 'use', 'instead', 'other', 'common'}


class Term:
    def __init__(self, term, definition, line, owner_id=None, target=None):
        self.term, self.definition, self.line, self.owner_id, self.target = term, definition, line, owner_id, target

    @property
    def key(self):
        return normalize(self.term)


def normalize(term):
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s/+-]', '', term.lower())).strip()


def narrative_id(text):
    return metadata.read(text).get('id')


def suggest_id(slug):
    out = ''
    for w in [w for w in slug.split('-') if w not in _QUESTION_WORDS] or slug.split('-'):
        if len(out) + len(w) + 1 > MAX_ID:
            break
        out = f'{out}-{w}' if out else w
    return out or slug[:MAX_ID]


def _shared(term):
    """Whether a row is a term the wiki shares: not a narrative's own notation ($x_t$) or a marker."""
    return not term.lstrip().startswith(('$', '[')) and bool(normalize(term))


def terms(text):
    """[Term] for the rows of the Terminology and Glossary tables that the wiki shares."""
    lines = text.split('\n')
    out = []
    for name in SECTIONS:
        span = numbering.section(text, name)
        for i in range(span[0], span[1]) if span else ():
            m = _ROW.match(lines[i])
            if not m or not _shared(m.group('term')):
                continue
            f = _FROM.match(m.group('definition'))
            if f:
                out.append(Term(m.group('term'), f.group('text'), i, f.group('id'), f.group('target')))
            else:
                out.append(Term(m.group('term'), m.group('definition'), i))
    return out


def _narratives(root):
    """{slug: text} for every recorded narrative that exists."""
    out = {}
    for slug in sorted(manifest.load(root, 'narratives')):
        path = os.path.join(root, layout.NARRATIVES, f'{slug}.md')
        if os.path.isfile(path):
            out[slug] = read_text(path)
    return out


def _owners(texts):
    """({id: slug}, {term key: [(slug, Term)]}) for the terms each narrative defines itself."""
    ids, owned = {}, {}
    for slug, text in texts.items():
        nid = narrative_id(text)
        if nid:
            ids.setdefault(nid, slug)
        for t in terms(text):
            if not t.owner_id:
                owned.setdefault(t.key, []).append((slug, t))
    return ids, owned


def _section_anchor(text, line):
    """The anchor of the ## or ### section holding a line."""
    heads = [h for h in numbering.headings(text) if h.line <= line and h.level in (2, 3)]
    return numbering.anchor(heads[-1].text) if heads else ''


def _owner_of(t, ids, owned, texts):
    """(slug, owner's Term) for a borrowed term, or (None, problem)."""
    slug = ids.get(t.owner_id)
    if slug is None:
        return None, f'"{t.term}" is borrowed from {t.owner_id}, which no narrative has as its ID'
    match = next((ot for s, ot in owned.get(t.key, []) if s == slug), None)
    if match is None:
        return None, f'"{t.term}" is borrowed from {t.owner_id}, which doesn\'t define it'
    return slug, match


def sync(root, text, own_slug):
    """(text, rows filled, problems): each borrowed row gets its owner's definition, word for word, and a link to its section."""
    texts = _narratives(root)
    texts[own_slug] = text
    ids, owned = _owners(texts)
    lines = text.split('\n')
    filled, problems = 0, []
    for t in terms(text):
        if not t.owner_id:
            continue
        slug, owner = _owner_of(t, ids, owned, texts)
        if slug is None:
            problems.append((t.line, owner))
            continue
        row = f'| **{t.term}** | {owner.definition} From [{t.owner_id}]({slug}.md#{_section_anchor(texts[slug], owner.line)}). |'
        if lines[t.line] != row:
            lines[t.line] = row
            filled += 1
    return '\n'.join(lines), filled, problems


def _links(root, rel, text):
    """[(line, match, target text or None)] for each link to a section of another narrative."""
    folder = os.path.dirname(os.path.join(root, rel))
    narratives = os.path.realpath(os.path.join(root, layout.NARRATIVES))
    lines = text.split('\n')
    kinds, _ = scan(lines)
    out = []
    for i, line in enumerate(lines):
        if kinds[i] != 'text':
            continue
        for m in _LINK.finditer(line):
            path = os.path.realpath(os.path.join(folder, m.group('file')))
            if os.path.dirname(path) == narratives and path != os.path.realpath(os.path.join(root, rel)):
                out.append((i, m, read_text(path) if os.path.isfile(path) else None))
    return out


def _moved(anchor, target):
    """The anchor a moved section has now: the same title under a new number, when exactly one matches."""
    title = re.sub(r'\A[0-9]+-?', '', anchor)
    found = [a for a in numbering.anchors(target) if re.sub(r'\A[0-9]+-?', '', a) == title]
    return found[0] if len(found) == 1 else None


def repair_links(root, rel, text):
    lines = text.split('\n')
    fixed = 0
    for i, m, target in reversed(_links(root, rel, text)):
        if target is None or m.group('anchor') in numbering.anchors(target):
            continue
        new = _moved(m.group('anchor'), target)
        if new:
            line = lines[i]
            lines[i] = line[:m.start('anchor')] + new + line[m.end('anchor'):]
            fixed += 1
    return '\n'.join(lines), fixed


def check_one(root, rel, text):
    """Findings (severity, code, line, message) for one narrative's ID, borrowed terms and links into other narratives."""
    out = []
    nid = narrative_id(text)
    slug = os.path.splitext(os.path.basename(rel))[0]
    if not nid:
        out.append(('error', 'NO_ID', 1, f'Metadata has no ID: give the narrative a short name for its subject, '
                                          f'such as finish-narrative.py {slug} --id {suggest_id(slug)}'))
    elif not ID.match(nid) or len(nid) > MAX_ID:
        out.append(('error', 'BAD_ID', 1, f'the ID {nid} must be kebab-case, at most {MAX_ID} characters'))
    texts = _narratives(root)
    texts[slug] = text
    ids, owned = _owners(texts)
    for t in terms(text):
        if t.owner_id:
            found, problem = _owner_of(t, ids, owned, texts)
            if found is None:
                out.append(('error', 'TERM_OWNER', t.line + 1, problem))
    for i, m, target in _links(root, rel, text):
        if target is not None and m.group('anchor') not in numbering.anchors(target):
            out.append(('error', 'NARRATIVE_ANCHOR', i + 1, f'{m.group("file")} has no section #{m.group("anchor")}'
                                                            + (' (finish-narrative.py repairs it)' if _moved(m.group('anchor'), target) else '')))
    return out


def check(root, fix=False):
    """[(severity, code, file, message)] across the narratives; with fix, moved links are repaired first."""
    texts = _narratives(root)
    out = []
    if fix:
        for slug, text in texts.items():
            rel = f'{layout.NARRATIVES}/{slug}.md'
            new, n = repair_links(root, rel, text)
            if n:
                write_text(os.path.join(root, rel), new)
                texts[slug] = new
    ids, owned = _owners(texts)
    seen = {}
    for slug, text in texts.items():
        rel = f'{layout.NARRATIVES}/{slug}.md'
        nid = narrative_id(text)
        if not nid:
            out.append(('warning', 'NARRATIVE_ID_MISSING', rel, f'no ID in its Metadata (finish-narrative.py {slug} --id {suggest_id(slug)})'))
        elif nid in seen:
            out.append(('error', 'NARRATIVE_ID_DUPLICATE', rel, f'its ID {nid} is also {seen[nid]}\'s; IDs are unique'))
        else:
            seen[nid] = slug
        for t in terms(text):
            if not t.owner_id:
                continue
            found, owner = _owner_of(t, ids, owned, texts)
            if found is None:
                out.append(('error', 'TERM_OWNER', f'{rel}:{t.line + 1}', owner))
            elif t.definition != owner.definition:
                out.append(('warning', 'TERM_DRIFT', f'{rel}:{t.line + 1}', f'"{t.term}" differs from {t.owner_id}\'s definition '
                                                                             f'(finish-narrative.py {slug} copies it)'))
        for i, m, target in _links(root, rel, text):
            if target is not None and m.group('anchor') not in numbering.anchors(target):
                out.append(('error', 'NARRATIVE_ANCHOR', f'{rel}:{i + 1}', f'{m.group("file")} has no section #{m.group("anchor")}'))
    for _, defs in sorted(owned.items()):
        slugs = sorted({s for s, _ in defs})
        if len(slugs) > 1:
            out.append(('warning', 'TERM_DEFINED_TWICE', f'{layout.NARRATIVES}/{slugs[1]}.md',
                        f'"{defs[0][1].term}" is defined in {", ".join(slugs)}: keep it in the narrative whose subject it is, '
                        'and borrow it in the others'))
    return out


def render(root):
    """The terms page: every term a narrative defines, its definition and where."""
    texts = _narratives(root)
    rows = []
    for slug, text in texts.items():
        nid = narrative_id(text) or slug
        for t in terms(text):
            if not t.owner_id:
                plain = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', t.definition)
                rows.append((t.key, f'| **{t.term}** | {plain} | [{nid}]({layout.NARRATIVES}/{slug}.md#{_section_anchor(text, t.line)}) |'))
    lines = ['# Terms of this wiki', '', GENERATED, '',
             'Each term is defined in one narrative. A narrative that uses it borrows that definition, word for word, '
             'and links to it, so the wiki describes each thing one way.', '']
    if rows:
        lines += ['| Term | Definition | Defined in |', '|---|---|---|'] + [r for _, r in sorted(rows)]
    else:
        lines.append('No terms yet.')
    return escape('\n'.join(lines) + '\n')[0]
