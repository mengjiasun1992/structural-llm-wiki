"""The wiki as a book (docs/book_design.md §5): its parts, its chapters in
teaching order, and the sources each chapter cites.

Parts follow the tag tree: a part per top-level tag, a section per child tag
under it, at any depth. A narrative is a chapter under its first primary tag
only; its other tags list it as see-also. Within a tag, chapters go in
teaching order (§5.2): after the narratives they're built on, then by
template, then by question.
"""

import heapq
import os

from . import citations, layout, metadata, tagtree
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
