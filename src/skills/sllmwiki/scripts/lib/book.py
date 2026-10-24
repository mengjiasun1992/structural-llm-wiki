"""The wiki as a book (docs/book_design.md §5): its parts, its chapters in
teaching order, the sources each chapter cites, and each chapter rewritten for
the book (§5.3).

Parts follow the tag tree: a part per top-level tag, a section per child tag
under it, at any depth. A narrative is a chapter under its first primary tag
only; its other tags list it as see-also. Within a tag, chapters go in
teaching order (§5.2): after the narratives they're built on, then by
template, then by question.
"""

import heapq
import os
import posixpath
import re

from . import citations, config, language, layout, manifest, mdlinks, metadata, numbering, tagtree
from .compat import mask_code_spans, scan
from .util import read_text

# §5.2: "what is X" before "how does X work" and "X or Y"; a wiki's own template goes last
TEMPLATE_ORDER = ('concept_brief_overview', 'survey', 'technical_brief_overview', 'comparison', 'case_study')


class Chapter:
    """A narrative in the book: its slug, question, template, the tag it's a
    chapter under, the narratives it's built on, and the sources it cites
    (in the order first cited)."""

    def __init__(self, slug, question, template, tag, built_on=(), sources=()):
        self.slug, self.question, self.template, self.tag = slug, question, template, tag
        self.built_on, self.sources = list(built_on), list(sources)

    def key(self):
        """The tie-break after built_on: template, then question."""
        rank = TEMPLATE_ORDER.index(self.template) if self.template in TEMPLATE_ORDER else len(TEMPLATE_ORDER)
        return (rank, self.question.casefold(), self.slug)


class Part:
    """A tag's place in the book: its chapters in teaching order, the chapters
    filed under it as supporting (see_also), and its child tags' parts
    (sections). depth is 0 for a part, 1 for its sections, and so on."""

    def __init__(self, tag, description, depth, chapters, see_also, sections):
        self.tag, self.description, self.depth = tag, description, depth
        self.chapters, self.see_also, self.sections = chapters, see_also, sections

    def walk(self):
        """This part and every section under it, depth first."""
        yield self
        for s in self.sections:
            yield from s.walk()


class Book:
    def __init__(self, parts, chapters, problems):
        self.parts, self.chapters, self.problems = parts, chapters, problems

    def order(self):
        """The chapters' slugs in reading order."""
        return [c for p in self.parts for s in p.walk() for c in s.chapters]

    def part_tags(self):
        """The tags with a part or section in the book."""
        return {s.tag for p in self.parts for s in p.walk()}

    def cited_by(self):
        """{source slug: [chapter slugs, in reading order]} for every cited source."""
        out = {}
        for c in self.order():
            for s in self.chapters[c].sources:
                out.setdefault(s, []).append(c)
        return out


def teaching_order(chapters):
    """The slugs of chapters ({slug: Chapter}) with each after the ones it's
    built on among them, ties broken by Chapter.key; chapters on or after a
    built_on cycle come last, by key."""
    bases = {s: {b for b in c.built_on if b in chapters and b != s} for s, c in chapters.items()}
    waiting = {s: len(b) for s, b in bases.items()}
    ready = [(chapters[s].key(), s) for s, n in waiting.items() if n == 0]
    heapq.heapify(ready)
    out = []
    while ready:
        _, s = heapq.heappop(ready)
        out.append(s)
        for t, b in bases.items():
            if s in b:
                waiting[t] -= 1
                if waiting[t] == 0:
                    heapq.heappush(ready, (chapters[t].key(), t))
    stuck = sorted((s for s in chapters if s not in out), key=lambda s: chapters[s].key())
    return out + stuck


def cycles(chapters):
    """The built_on cycles among chapters, each a sorted list of slugs
    (strongly connected components with more than one chapter, or a chapter
    built on itself)."""
    index, low, stack, on, out = {}, {}, [], set(), []

    def visit(s):
        index[s] = low[s] = len(index)
        stack.append(s)
        on.add(s)
        for b in chapters[s].built_on:
            if b not in chapters:
                continue
            if b not in index:
                visit(b)
                low[s] = min(low[s], low[b])
            elif b in on:
                low[s] = min(low[s], index[b])
        if low[s] == index[s]:
            comp = []
            while True:
                t = stack.pop()
                on.discard(t)
                comp.append(t)
                if t == s:
                    break
            if len(comp) > 1 or s in chapters[s].built_on:
                out.append(sorted(comp))

    for s in sorted(chapters):
        if s not in index:
            visit(s)
    return sorted(out)


def _chapters(root, tree):
    """{slug: Chapter} for every narrative in the manifest with a file and a
    primary tag in the tree (wiki-check reports the others)."""
    out = {}
    for slug, entry in tree.narratives.items():
        path = os.path.join(root, layout.NARRATIVES, f'{slug}.md')
        primary = [t for t in (entry.get('tags') or {}).get('primary') or [] if t in tree.tags]
        if not os.path.isfile(path) or not primary:
            continue
        text = read_text(path)
        sources = list(dict.fromkeys(c.slug for c in citations.cites(text) if c.slug))
        out[slug] = Chapter(slug, metadata.title(text) or slug, entry.get('template'), primary[0],
                            list(entry.get('built_on') or {}), sources)
    return out


def _part(tree, tag, depth, chapters, seen):
    """The Part for tag, or None when neither it nor a tag under it has a chapter
    or a see-also. seen keeps a tag on a cycle (TAG_CYCLE) from being visited twice."""
    seen.add(tag)
    sections = [p for p in (_part(tree, t, depth + 1, chapters, seen) for t in tree.children(tag) if t not in seen) if p]
    mine = {s: c for s, c in chapters.items() if c.tag == tag}
    filed = tree.narratives_of(tag)
    see_also = sorted((s for s in filed['primary'] + filed['supporting'] if s in chapters and s not in mine),
                      key=lambda s: chapters[s].key())
    if not (mine or see_also or sections):
        return None
    return Part(tag, tree.tags[tag].get('description') or '', depth, teaching_order(mine), see_also, sections)


def model(root):
    """The Book for the wiki at root."""
    tree = tagtree.load(root)
    chapters = _chapters(root, tree)
    seen = set()
    parts = [p for p in (_part(tree, t, 0, chapters, seen) for d, t in tree.walk() if d == 0 and t not in seen) if p]
    problems = [('BOOK_CYCLE', c[0], f'narratives built on each other in a cycle: {", ".join(c)}')
                for c in cycles(chapters)]
    return Book(parts, chapters, problems)


# Labels: the book's anchors, unique across it (design §6.2), as MyST targets
CONTENTS = 'book--contents'
_DEST = re.compile(r'(?P<image>!?)\[(?P<text>(?:[^\]\\\n]|\\.)*)\]\((?P<dest>[^)\s]*)\)')
_SCHEME = re.compile(r'[A-Za-z][A-Za-z0-9+.-]*:')


def chapter_label(slug):
    return f'ch--{slug}'


def section_label(slug, anchor):
    """A section's label: its chapter and its GitHub anchor, with any non-ASCII
    character spelled out, since docutils drops them from ids."""
    return f'{slug}--' + ''.join(c if c.isascii() else f'u{ord(c):x}' for c in anchor)


def source_label(slug):
    return f'src--{slug}'


def part_label(tag):
    return f'part--{tag}'


class Rewritten:
    """A chapter as the book has it: its text, the problems found (code, where,
    message), the sources it links to, and the figures it shows (paths under
    the narratives folder)."""

    def __init__(self, text, problems, sources, figures):
        self.text, self.problems, self.sources, self.figures = text, problems, sources, figures


def _version_line(text, pack):
    m = metadata.read(text)
    parts = [f'{pack.t(label)} {value}' for label, value in (('Version', m['version']), ('Last modified', m['last_modified'])) if value]
    return f'*{" · ".join(parts)}*' if parts else None


def rewrite(root, book, slug):
    """Chapter slug of book rewritten for the book (design §5.3): a label
    before every heading; citations and links to sources to their Appendix A
    entries; links to narratives, sections and tag pages to their labels; the
    Metadata section replaced by a version line under the title. A link the
    book can't resolve is BOOK_LINK, a figure that isn't there BOOK_FIGURE; a
    link to any other file in the repository keeps only its text."""
    rel = f'{layout.NARRATIVES}/{slug}.md'
    text = read_text(os.path.join(root, rel))
    _, pack = language.for_narrative(text, config.get(root).settings['language'])
    version = _version_line(text, pack)
    text = _without_metadata(text)
    problems, sources, figures = [], [], []
    own = numbering.anchors(text)
    known = set(manifest.load(root, 'sources'))

    def target(dest, n):
        """The book's link for dest, or None to keep only the text."""
        path, frag = mdlinks.split(dest)
        where = f'{rel}:{n}'
        if not path:
            if frag in own:
                return '#' + section_label(slug, frag)
            problems.append(('BOOK_LINK', where, f'{dest}: this narrative has no section #{frag}'))
            return None
        to = mdlinks.resolve(rel, path)
        folder, name = posixpath.split(to or '')
        base = name[:-3] if name.endswith('.md') else None
        if folder == layout.SOURCES and base:
            if base not in known:
                problems.append(('BOOK_LINK', where, f'{dest}: no source {base}'))
                return None
            sources.append(base)
            return '#' + source_label(base)
        if folder == layout.NARRATIVES and base:
            if base not in book.chapters:
                problems.append(('BOOK_LINK', where, f'{dest}: {base} isn\'t a chapter of the book'))
                return None
            if not frag:
                return '#' + chapter_label(base)
            if frag not in _anchors(root, base):
                problems.append(('BOOK_LINK', where, f'{dest}: {base} has no section #{frag}'))
                return None
            return '#' + section_label(base, frag)
        if folder == layout.TAGS_DIR and base:
            return '#' + part_label(base) if base in book.part_tags() else None
        if to == layout.INDEX:
            return '#' + CONTENTS
        return None

    lines = text.split('\n')
    kinds, _ = scan(lines)
    for i, line in enumerate(lines):
        if kinds[i] != 'text':
            continue
        masked, out, at = mask_code_spans(line), [], 0
        for m in _DEST.finditer(masked):
            dest = line[m.start('dest'):m.end('dest')]
            if not dest or _SCHEME.match(dest):
                continue
            if m.group('image'):
                fig = mdlinks.resolve(rel, mdlinks.split(dest)[0])
                if fig is None or not os.path.isfile(os.path.join(root, fig)):
                    problems.append(('BOOK_FIGURE', f'{rel}:{i + 1}', f'{dest}: no such figure'))
                else:
                    figures.append(posixpath.relpath(fig, layout.NARRATIVES))
                continue
            new = target(dest, i + 1)
            out.append(line[at:m.start()])
            out.append(f'[{line[m.start("text"):m.end("text")]}]({new})' if new else line[m.start('text'):m.end('text')])
            at = m.end()
        lines[i] = ''.join(out) + line[at:]
    for anchor, h in sorted(own.items(), key=lambda x: -x[1].line):
        lines.insert(h.line, f'({chapter_label(slug) if h.level == 1 else section_label(slug, anchor)})=')
        if h.level == 1 and version:
            lines.insert(h.line + 2, '\n' + version)
    return Rewritten('\n'.join(lines), problems, list(dict.fromkeys(sources)), list(dict.fromkeys(figures)))


def _without_metadata(text):
    """text without its Metadata section, which the book replaces by a version line."""
    span = numbering.section(text, 'Metadata')
    lines = text.split('\n')
    if span:
        del lines[span[0]:span[1]]
    return '\n'.join(lines).rstrip('\n') + '\n'


def _anchors(root, slug):
    return numbering.anchors(_without_metadata(read_text(os.path.join(root, layout.NARRATIVES, f'{slug}.md'))))
