"""Prerequisites (design doc §4.5.2): the narratives whose concepts a narrative uses
without explaining them, which a reader reads first. finish-narrative records a
narrative's direct ones (--prerequisite) in its manifest entry, pinned like
built_on; this module writes what follows from them into every narrative, in its
language, and checks them.

    # How does attention work?

    *About 9 min read. Read first: [What is a token?](what-is-a-token.md) ([Before you read](#81-before-you-read)).*
    …
    ## 8. Appendix

    <!-- sllmwiki:reading-order: … -->

    ### 8.1 Before you read

    - [What is a token?](what-is-a-token.md) (about 6 min): <its first key takeaway>

    ### 8.2 Where to go next

    - [How does a transformer work?](how-does-a-transformer-work.md) (about 12 min): <its first key takeaway>

    <!-- /sllmwiki:reading-order -->

    - <the writer's own next reads: siblings, deeper questions>

Before you read lists the prerequisites; Where to go next, the narratives that
list this one as theirs, then the writer's own next reads, after the region's
end, which a rewrite keeps. A ### Where to go next the writer put in the Appendix
is taken in the same way. What's generated counts neither as words nor as a
change to the narrative (metadata.without_generated).
"""

import os
import re

from . import compat, language, layout, manifest, metadata, numbering
from .util import read_text, write_text

BEFORE, NEXT, APPENDIX = 'Before you read', 'Where to go next', 'Appendix'
ABOUT = 'about {n} min'
START = metadata.REGION_START + ': written by sllmwiki finish-narrative and wiki-check --fix; your own next reads go after its end -->'
END = metadata.REGION_END
BOTTOM = ('SMEs', 'References', 'Metadata')  # the shared sections after the Appendix
_CITES = re.compile(r'[ \t]*\[\\\[[0-9]+\\\]\]\([^)]*\)(?:[ \t]*,[ \t]*\[\\\[[0-9]+\\\]\]\([^)]*\))*')
_MARK = re.compile(r'[ \t]*(?:\[→\]|\[->\]|\[\?\])(?!\()')
_TO = re.compile(r'\]\((?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.md(?:#[^)\s]*)?\)')
_TERM = re.compile(r'\|\s*\*\*(?P<term>[^*|]+)\*\*\s*\|')


def graph(narratives):
    """{slug: [its prerequisites]} from the narratives' manifest."""
    return {slug: list((e or {}).get('prerequisites') or {}) for slug, e in narratives.items()}


def reach(g, slug):
    """Every narrative a reader of slug reads first, directly or through another."""
    seen, todo = set(), list(g.get(slug, []))
    while todo:
        s = todo.pop()
        if s not in seen:
            seen.add(s)
            todo += g.get(s, [])
    return seen


def cycles(g):
    """The narratives that are, through their prerequisites, their own: each cycle a sorted list."""
    out, seen = [], set()
    for s in sorted(g):
        if s not in seen and s in reach(g, s):
            group = sorted({t for t in reach(g, s) if s in reach(g, t)} | {s})
            seen.update(group)
            out.append(group)
    return out


def indirect(g):
    """[(slug, prerequisite, through)] for a prerequisite listed as direct that another of slug's prerequisites already needs."""
    return [(s, p, next(q for q in g[s] if q != p and p in reach(g, q))) for s in sorted(g) for p in g[s]
            if any(q != p and p in reach(g, q) for q in g[s])]


def dependents(g, slug):
    return [s for s in sorted(g) if slug in g[s]]


class Info:
    """What a row says about a narrative: its question, its first key takeaway, its reading time."""

    def __init__(self, text):
        self.title = metadata.title(text) or ''
        self.minutes = metadata.reading(text)[1]
        self.takeaway = takeaway(text)


class Infos(dict):
    """{slug: Info or None}, read from the narratives' files as they're asked for."""

    def __init__(self, root):
        super().__init__()
        self.root = root

    def __missing__(self, slug):
        path = os.path.join(self.root, layout.NARRATIVES, f'{slug}.md')
        self[slug] = Info(read_text(path)) if os.path.isfile(path) else None
        return self[slug]


def takeaway(text):
    """A narrative's first key takeaway, without its citations and markers, or ''."""
    lines = metadata.section_lines(text, 'Abstract')
    labels = {n.lower() for n in language.names('Key takeaways')}
    at = next((i for i, line in enumerate(lines) if (m := re.match(r'\s*\*\*(.+?):?\*\*', line)) and m.group(1).rstrip(':').lower() in labels), None)
    if at is None:
        return ''
    first = next((line for line in lines[at + 1:] if re.match(r'\s*[-*+] ', line)), '')
    first = re.sub(r'\A\s*[-*+]\s+', '', first)
    return re.sub(r'\s+([.,;:!?])', r'\1', _MARK.sub('', _CITES.sub('', first))).strip()


def _names(english):
    return {n.lower() for n in language.names(english)}


def _bracketed(title):
    return title.replace('[', '\\[').replace(']', '\\]')


def _row(slug, info, pack):
    row = f'- [{_bracketed(info.title)}]({slug}.md) ({pack.t(ABOUT).replace("{n}", str(info.minutes))})' + (f': {info.takeaway}' if info.takeaway else '')
    return compat.escape(row)[0]


def _span(text, english, level):
    """(start, end) of the first section of level titled english in any language, or None."""
    heads = numbering.headings(text)
    want = _names(english)
    for h in heads:
        if h.level == level and re.sub(r'\s*\(optional\)\Z', '', h.title, flags=re.I).lower() in want:
            end = next((x.line for x in heads if x.line > h.line and x.level <= level), len(text.split('\n')))
            return h.line, end
    return None


def _splice(lines, start, end, new):
    """lines with lines[start:end] replaced by new, one blank line on each side of it (none when new is empty)."""
    before, after = lines[:start], lines[end:]
    while before and not before[-1].strip():
        before.pop()
    while after and not after[0].strip():
        after.pop(0)
    if not new:
        return before + ([''] + after if after else [''])
    return before + [''] + new + [''] + after


def _trim(lines):
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def _take_region(lines):
    """(lines without the region and the writer's next reads after it, those next reads)."""
    start = next((i for i, line in enumerate(lines) if line.startswith(metadata.REGION_START)), None)
    if start is None:
        return lines, []
    end = next((i for i in range(start, len(lines)) if lines[i].strip() == END), start)
    heads = [h.line for h in numbering.headings('\n'.join(lines)) if h.level <= 3]
    stop = next((h for h in heads if h > end), len(lines))
    return _splice(lines, start, stop, []), _trim(lines[end + 1:stop])


def _appendix(lines, pack, create):
    """(lines, (start, end) of the Appendix): with create, one is added before SMEs, References or Metadata when there's none."""
    text = '\n'.join(lines)
    span = _span(text, APPENDIX, 2)
    if span or not create:
        return lines, span
    heads = [h for h in numbering.headings(text) if h.level == 2]
    bottom = set().union(*(_names(b) for b in BOTTOM))
    at = next((h.line for h in heads if h.title.lower() in bottom), len(lines))
    lines = _splice(lines, at, at, [f'## {pack.t(APPENDIX)}'])
    return lines, _span('\n'.join(lines), APPENDIX, 2)


def render(text, firsts, nexts, infos, pack):
    """text with its reading-order region and Read first sentence for these prerequisites and the narratives
    that need it (slugs, in order), renumbered; an Appendix the region leaves empty goes. Unchanged when there's
    nothing to write and nothing was written."""
    original = text.split('\n')
    lines, own = _take_region(original)
    took = lines != original
    lines, span = _appendix(lines, pack, False)
    while span:  # a ### Where to go next of the writer's own
        sub = _span('\n'.join(lines[span[0] + 1:span[1]]), NEXT, 3)
        if not sub:
            break
        a, b = span[0] + 1 + sub[0], span[0] + 1 + sub[1]
        own = _trim(lines[a + 1:b]) + ([''] if own else []) + own
        lines, took = _splice(lines, a, b, []), True
        lines, span = _appendix(lines, pack, False)
    linked = set(firsts) | set(nexts)
    own = _trim([line for line in own if not (re.match(r'\s*[-*+] ', line) and (m := _TO.search(line)) and m.group('slug') in linked)])
    block = []
    if firsts:
        block += ['', f'### {pack.t(BEFORE)}', ''] + [_row(s, infos[s], pack) for s in firsts]
    if nexts or own:
        block += ['', f'### {pack.t(NEXT)}', ''] + [_row(s, infos[s], pack) for s in nexts]
    if block:
        lines, span = _appendix(lines, pack, True)
        heads = [h for h in numbering.headings('\n'.join(lines)) if span[0] < h.line < span[1] and h.level == 3]
        at = heads[0].line if heads else span[1]
        lines = _splice(lines, at, at, [START, ''] + _trim(block) + ['', END] + ([''] + own if own else []))
    elif took and span and not any(line.strip() for line in lines[span[0] + 1:span[1]]):
        lines = _splice(lines, span[0], span[1], [])
    text = '\n'.join(lines)
    if block or took:
        text = numbering.renumber(text)[0]
    sentence = ''
    if firsts:
        found = [a for a, h in numbering.anchors(text).items() if h.level == 3 and h.title.lower() in _names(BEFORE)]
        links = ', '.join(f'[{_bracketed(infos[s].title)}]({s}.md)' for s in firsts)
        sentence = compat.escape(pack.t(metadata.READ_FIRST).replace('{links}', links).replace('{section}', f'[{pack.t(BEFORE)}](#{found[0]})'))[0]
    return metadata.with_read_first(text, sentence) if sentence or metadata.read_first(text) else text


def regenerate(root, slug, text, g, infos, default=language.DEFAULT):
    """A narrative's text with its region and Read first sentence current for the prerequisites graph g."""
    pack = language.for_narrative(text, default)[1]
    firsts = [p for p in g.get(slug, []) if infos[p]]
    nexts = sorted((s for s in dependents(g, slug) if infos[s]), key=lambda s: (infos[s].title.lower(), s))
    return render(text, firsts, nexts, infos, pack)


def sync(root, write=False):
    """(findings, changed paths): each narrative whose region or Read first sentence isn't current; with write,
    rewritten, and the pins on it that matched it before moved to its new text (nothing a reader reads changed)."""
    from . import config
    narratives = manifest.load(root, 'narratives')
    g, infos = graph(narratives), Infos(root)
    default = config.get(root).settings['language']
    findings, changed, before = [], [], {}
    for slug in sorted(narratives):
        rel = f'{layout.NARRATIVES}/{slug}.md'
        if not infos[slug]:
            continue
        text = read_text(os.path.join(root, rel))
        new = regenerate(root, slug, text, g, infos, default)
        if new == text:
            continue
        if write:
            before[slug] = text
            write_text(os.path.join(root, rel), new)
            changed.append(rel)
        else:
            findings.append(('error', 'READING_ORDER_OUTDATED', rel, f'{slug}: its Before you read, Where to go next or Read first line '
                                                                     'is out of date (wiki-check --fix rewrites it)'))
    if before:
        manifest.repin(root, before)
    return findings, changed


def check(root, narratives):
    """[(severity, code, file, message)] for the prerequisites the narratives' manifest records."""
    g = graph(narratives)
    out = []
    for slug in sorted(g):
        rel = f'{layout.NARRATIVES}/{slug}.md'
        for p, pin in ((narratives[slug] or {}).get('prerequisites') or {}).items():
            path = os.path.join(root, layout.NARRATIVES, f'{p}.md')
            if not os.path.isfile(path):
                out.append(('error', 'PREREQUISITE_UNKNOWN', layout.NARRATIVES_MANIFEST, f'{slug}: its prerequisite {p} is no narrative; '
                                                                                         'record the right ones with finish-narrative --prerequisite'))
            elif not manifest.pin_matches(read_text(path), pin):
                out.append(('warning', 'PREREQUISITE_CHANGED', rel, f'{slug} needs {p} first, which changed since: check it still explains '
                                                                    f'what {slug} uses without explaining, and lint it'))
    for group in cycles(g):
        out.append(('error', 'PREREQUISITE_CYCLE', layout.NARRATIVES_MANIFEST, f'{", ".join(group)} are each other\'s prerequisites: '
                                                                               'a reader can\'t read either first; drop the one that is only related'))
    for s, p, q in indirect(g):
        out.append(('warning', 'PREREQUISITE_INDIRECT', f'{layout.NARRATIVES}/{s}.md', f'{s} lists {p}, which its prerequisite {q} already needs: '
                                                                                       f'leave {p} out (finish-narrative --prerequisite with the others)'))
    return out


# Proposals: the evidence that one narrative uses another's concepts

def _terms(text):
    """The terms a narrative defines: the bold first cells of its Terminology and Glossary tables, lowercase."""
    out = set()
    for name in ('Terminology', 'Glossary'):
        for line in metadata.section_lines(text, name):
            m = _TERM.match(line.strip())
            if m:
                out.add(m.group('term').strip().lower())
    return out


def _read_part(text):
    """What a reader of the narrative reads, for finding what it uses: no generated part, next reads, Terminology,
    Glossary, References, SMEs or Metadata, and link targets left as their text."""
    lines = text.split('\n')
    if any(line.startswith(metadata.REGION_START) for line in lines):
        lines = _take_region(lines)[0]
    text = metadata.without_generated('\n'.join(lines))
    for name, level in ((NEXT, 2), (NEXT, 3), ('Terminology', 2), ('Glossary', 3), ('SMEs', 2), ('References', 2), ('Metadata', 2)):
        span = _span(text, name, level)
        if span:
            lines = text.split('\n')
            text = '\n'.join(_splice(lines, span[0], span[1], []))
    return text


def propose(root, slugs=None):
    """{slug: {'prerequisites': [recorded], 'candidates': {other: evidence}, 'unused': [recorded with no evidence]}}:
    for each narrative (or those named), every other narrative it builds on, links to, or uses a defined term of;
    evidence is {'built_on': bool, 'links': n, 'terms': [...], 'cycle': bool, 'indirect': bool}."""
    narratives = manifest.load(root, 'narratives')
    texts = {}
    for s in narratives:
        path = os.path.join(root, layout.NARRATIVES, f'{s}.md')
        if os.path.isfile(path):
            texts[s] = read_text(path)
    defined = {s: _terms(t) for s, t in texts.items()}
    g = graph(narratives)
    out = {}
    for slug in sorted(slugs or texts):
        if slug not in texts:
            raise ValueError(f'no narrative {slug}')
        body = _read_part(texts[slug])
        prose = re.sub(r'\]\([^)]*\)', ']', body).lower()
        found = {}
        for other in sorted(texts):
            if other == slug:
                continue
            links = len([m for m in _TO.finditer(body) if m.group('slug') == other])
            terms = sorted(t for t in defined[other] - defined[slug] if re.search(r'(?<![\w-])' + re.escape(t) + r'(?![\w-])', prose))
            based = other in ((narratives.get(slug) or {}).get('built_on') or {})
            if links or terms or based:
                found[other] = {'built_on': based, 'links': links, 'terms': terms, 'cycle': slug in reach(g, other) or other == slug,
                                'indirect': any(other in reach(g, p) for p in g.get(slug, []))}
        recorded = g.get(slug, [])
        out[slug] = {'prerequisites': recorded, 'candidates': {o: e for o, e in found.items() if o not in recorded},
                     'unused': [p for p in recorded if p not in found or not (found[p]['links'] or found[p]['terms'])]}
    return out


def move_next(text, default=language.DEFAULT):
    """(text, moved): a ## Where to go next section of the narrative's body moved into its Appendix, as the
    writer's own next reads; its Words and reading time kept current."""
    span = _span(text, NEXT, 2)
    if not span:
        return text, False
    pack = language.for_narrative(text, default)[1]
    lines = text.split('\n')
    body = _trim(lines[span[0] + 1:span[1]])
    kinds, _ = compat.scan(body)
    body = [('#' + line if kinds[i] == 'text' and re.match(r'#{2,5} ', line) else line) for i, line in enumerate(body)]
    lines = _splice(lines, span[0], span[1], [])
    lines, app = _appendix(lines, pack, True)
    lines = _splice(lines, app[1], app[1], [f'### {pack.t(NEXT)}', ''] + body)
    text = metadata.with_reading_line(numbering.renumber('\n'.join(lines))[0])
    if metadata.read(text)['words']:
        text = metadata.write(text, {'words': metadata.reading_label(text)})
    return text, True
