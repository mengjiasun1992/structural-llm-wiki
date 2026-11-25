"""The wiki as a book (docs/book_design.md §5): its parts, its chapters in
teaching order, the sources each chapter cites, and each chapter rewritten for
the book (§5.3).

Parts follow the tag tree, three levels deep: a volume per top-level tag, in
the index's reading order (roots after the roots they need), a chapter per
child tag, a sub-chapter per grandchild, numbered by their place (Volume 1,
Chapter 1.2, 1.2.3); a tag deeper than that folds into its sub-chapter, its
narratives with it. The numbers are the book's alone: they move whenever a tag
does, so the wiki's pages never show them. A narrative is a chapter under its home, its most specific primary
tag (lib/readingorder.py); its other tags list it as see-also. Within a tag,
chapters go in teaching order (§5.2): after their prerequisites and the
narratives they're built on, then by template, then by question.
"""

import hashlib
import heapq
import os
import posixpath
import re

from . import citations, compat, config, language, layout, manifest, markers, mdlinks, metadata, annotations, numbering, readingorder, tagtree
from .compat import mask_code_spans, scan
from . import prerequisites
from .util import read_text

TEMPLATE_ORDER = readingorder.TEMPLATE_ORDER  # §5.2


class Chapter:
    """A narrative in the book: its slug, question, template, the tag it's a
    chapter under, the narratives it's built on, and the sources it cites
    (in the order first cited)."""

    def __init__(self, slug, question, template, tag, built_on=(), sources=(), prerequisites=()):
        self.slug, self.question, self.template, self.tag = slug, question, template, tag
        self.built_on, self.sources, self.prerequisites = list(built_on), list(sources), list(prerequisites)

    def key(self):
        """The tie-break after prerequisites and built_on: template, then question."""
        return (readingorder.template_rank(self.template), self.question.casefold(), self.slug)


class Part:
    """A tag's place in the book: its chapters in teaching order, the chapters
    filed under it as supporting (see_also), and its child tags' parts
    (sections). depth is 0 for a volume, 1 for a chapter, 2 for a sub-chapter; number
    is its place ('1', '1.2', '1.2.3'); folded, the deeper tags it holds."""

    def __init__(self, tag, description, depth, chapters, see_also, sections, folded=()):
        self.tag, self.description, self.depth = tag, description, depth
        self.chapters, self.see_also, self.sections = chapters, see_also, sections
        self.folded, self.number = set(folded), ''

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

    def part_of(self, tag):
        """The tag of the part that holds tag: its own, or the sub-chapter it folds into; None outside the book."""
        return next((s.tag for p in self.parts for s in p.walk() if tag == s.tag or tag in s.folded), None)

    def cited_by(self):
        """{source slug: [chapter slugs, in reading order]} for every cited source."""
        out = {}
        for c in self.order():
            for s in self.chapters[c].sources:
                out.setdefault(s, []).append(c)
        return out


def teaching_order(chapters):
    """The slugs of chapters ({slug: Chapter}) with each after its prerequisites and the ones it's built on
    among them, ties broken by Chapter.key; a built_on a prerequisite contradicts (the base needs the chapter
    first, directly or not) is left out; chapters on or after a cycle come last, by key."""
    needs = {s: c.prerequisites for s, c in chapters.items()}
    bases = {s: {b for b in c.prerequisites + [b for b in c.built_on if s not in prerequisites.reach(needs, b)] if b in chapters and b != s}
             for s, c in chapters.items()}
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
        home = readingorder.home(tree, (entry.get('tags') or {}).get('primary'))
        if not os.path.isfile(path) or not home:
            continue
        text = read_text(path)
        sources = list(dict.fromkeys(c.slug for c in citations.cites(text) if c.slug))
        out[slug] = Chapter(slug, metadata.title(text) or slug, entry.get('template'), home,
                            list(entry.get('built_on') or {}), sources, list(entry.get('prerequisites') or {}))
    return out


DEPTH = 3  # volumes, chapters, sub-chapters: a deeper tag folds into its sub-chapter


def _below(tree, tag, seen):
    """Every tag under tag, at any depth, each once."""
    out = []
    for t in tree.children(tag):
        if t not in seen:
            seen.add(t)
            out += [t] + _below(tree, t, seen)
    return out


def _part(tree, tag, depth, chapters, seen):
    """The Part for tag, or None when neither it nor a tag under it has a chapter
    or a see-also. seen keeps a tag on a cycle (TAG_CYCLE) from being visited twice."""
    seen.add(tag)
    folded = _below(tree, tag, seen) if depth == DEPTH - 1 else []
    sections = [] if folded or depth == DEPTH - 1 else [
        p for p in (_part(tree, t, depth + 1, chapters, seen) for t in tree.children(tag) if t not in seen) if p]
    held = {tag, *folded}
    mine = {s: c for s, c in chapters.items() if c.tag in held}
    filed = [s for t in [tag] + folded for kind in ('primary', 'supporting') for s in tree.narratives_of(t)[kind]]
    see_also = sorted({s for s in filed if s in chapters and s not in mine}, key=lambda s: chapters[s].key())
    if not (mine or see_also or sections):
        return None
    return Part(tag, tree.tags[tag].get('description') or '', depth, teaching_order(mine), see_also, sections, folded)


def _number(parts, prefix=''):
    for i, p in enumerate(parts, 1):
        p.number = f'{prefix}{i}'
        _number(p.sections, p.number + '.')


def model(root):
    """The Book for the wiki at root."""
    tree = tagtree.load(root)
    chapters = _chapters(root, tree)
    seen = set()
    roots = readingorder.Order(tree, {s: c.question for s, c in chapters.items()}).roots()
    parts = [p for p in (_part(tree, t, 0, chapters, seen) for d, t in tree.walk(roots) if d == 0 and t not in seen) if p]
    _number(parts)
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
    message) and the link each is about (targets), the sources it links to, and
    the figures it shows (paths under the narratives folder)."""

    def __init__(self, text, problems, sources, figures, targets=()):
        self.text, self.problems, self.sources, self.figures = text, problems, sources, figures
        self.targets = list(targets)


def _version_line(text, pack):
    """The line under a chapter's title: when it last changed and its reading time; the narrative's version
    number is bookkeeping, not for a reader."""
    m = metadata.read(text)
    parts = [m['last_modified']] if m['last_modified'] else []
    parts.append(pack.t('{n} min read').replace('{n}', str(metadata.reading(text)[1])))
    return f'*{" · ".join(parts)}*'


def rewrite(root, book, slug):
    """Chapter slug of book rewritten for the book (design §5.3): a label
    before every heading; citations and links to sources to their Appendix A
    entries; links to narratives, sections and tag pages to their labels; what
    isn't for a reader left out (_for_reader), Metadata replaced by a line under
    the title with the date and reading time. A link the
    book can't resolve is BOOK_LINK, a figure that isn't there BOOK_FIGURE; a
    link to any other file in the repository keeps only its text."""
    rel = f'{layout.NARRATIVES}/{slug}.md'
    text = read_text(os.path.join(root, rel))
    _, pack = language.for_narrative(text, config.get(root).settings['language'])
    version = _version_line(text, pack)
    text, renamed = _for_reader(text)
    text = metadata.without_reading_line(text)  # the line under the title has the reading time
    problems, targets, sources, figures = [], [], [], []
    own = numbering.anchors(text)

    def fail(dest, code, where, message):
        problems.append((code, where, message))
        targets.append(dest)
    known = set(manifest.load(root, 'sources'))

    def target(dest, n):
        """The book's link for dest, or None to keep only the text."""
        path, frag = mdlinks.split(dest)
        where = f'{rel}:{n}'
        if not path:
            if renamed.get(frag):
                return '#' + section_label(slug, renamed[frag])
            if frag in renamed:  # a section the book leaves out
                return None
            fail(dest, 'BOOK_LINK', where, f'{dest}: this narrative has no section #{frag}')
            return None
        to = mdlinks.resolve(rel, path)
        folder, name = posixpath.split(to or '')
        base = name[:-3] if name.endswith('.md') else None
        if folder == layout.SOURCES and base:
            if base not in known:
                fail(dest, 'BOOK_LINK', where, f'{dest}: no source {base}')
                return None
            sources.append(base)
            return '#' + source_label(base)
        if folder == layout.NARRATIVES and base:
            if base not in book.chapters:
                fail(dest, 'BOOK_LINK', where, f'{dest}: {base} isn\'t a chapter of the book')
                return None
            if not frag:
                return '#' + chapter_label(base)
            theirs = _anchors(root, base)
            if frag not in theirs:
                fail(dest, 'BOOK_LINK', where, f'{dest}: {base} has no section #{frag}')
                return None
            return '#' + section_label(base, theirs[frag]) if theirs[frag] else None
        if folder == layout.TAGS_DIR and base:
            held = book.part_of(base)
            return '#' + part_label(held) if held else None
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
                    fail(dest, 'BOOK_FIGURE', f'{rel}:{i + 1}', f'{dest}: no such figure')
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
    del lines[:scan(lines)[0].count('front')]  # YAML front matter (the Obsidian add-on's) means nothing in a book
    while lines and not lines[0].strip():
        del lines[0]
    return Rewritten('\n'.join(lines), problems, list(dict.fromkeys(sources)), list(dict.fromkeys(figures)), targets)


def without_comments(text):
    """text without its HTML comments (<!-- … -->), outside code: authoring markers, never for a reader, and a
    comment holding "--" isn't XML, which breaks an EPUB's XHTML (issue #214). A line left empty by it goes."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    out, inside = [], False
    for i, line in enumerate(lines):
        if not inside and (kinds[i] != 'text' or '<!--' not in line):
            out.append(line)
            continue
        masked, kept, at = mask_code_spans(line), [], 0
        while at <= len(line):
            j = masked.find('-->' if inside else '<!--', at)
            if j < 0:
                if not inside:
                    kept.append(line[at:])
                break
            if not inside:
                kept.append(line[at:j])
            at, inside = j + (3 if inside else 4), not inside
        left = ''.join(kept)
        if left.strip():
            out.append(left.rstrip())
    return '\n'.join(out)


LEFT_OUT = ('SMEs', 'Metadata', 'Sources read')  # sections the book leaves out: who to ask (people's names, in a file that
# travels), the narrative's bookkeeping, and the sources it read, which Appendix A lists with their abstracts


def _for_reader(text):
    """(text without the sections in LEFT_OUT and its headings renumbered to close the gaps, {anchor in the
    narrative: its anchor in the book, or None for a section left out})."""
    before = numbering.anchors(text)
    for name in LEFT_OUT:
        span = numbering.section(text, name)
        if span:
            lines = text.split('\n')
            del lines[span[0]:span[1]]
            text = '\n'.join(lines)
    text = text.rstrip('\n') + '\n'
    kept = numbering.anchors(text)  # the headings kept, by their old numbers; renumbering keeps their lines
    text, _ = numbering.renumber(text)
    by_line = {h.line: a for a, h in numbering.anchors(text).items()}
    return text, {a: (by_line[kept[a].line] if a in kept else None) for a in before}


def _anchors(root, slug):
    """{anchor in narrative slug: its anchor in the book, or None for a section left out}."""
    return _for_reader(read_text(os.path.join(root, layout.NARRATIVES, f'{slug}.md')))[1]


# The generated pages (design §5.1), their labels and files in the staged folder
COVER, ABOUT = 'book--cover', 'book--about'
APPENDICES = (('book--sources', 'Appendix A: Sources', 'appendix-sources'),
              ('book--glossary', 'Appendix B: Glossary', 'appendix-glossary'),
              ('book--questions', 'Appendix C: Open questions', 'appendix-questions'))
FRONT = ("The narratives in this book are the wiki owner's work. Every source belongs to its authors: "
         'the book links to it and quotes it briefly, but never copies it.',
         'The narratives were written by an LLM and reviewed by the owner.',
         'This book is a snapshot of the wiki at the commit on its cover.')
MADE = ('Made by {tool} and {models}, from {source}.', 'Made by {tool}, from {source}.')  # with models, without
TITLE_MARK = '📖'
CITING = ("A number in brackets, such as [3], is a citation: it links to the source's entry in Appendix A, "
          'which links to the original.')
_CELL = re.compile(r'(?<!\\)\|')


def _escape(text):
    return compat.escape(text or '')[0].strip()


def title(tag, text):
    """A part's title: its tag in words, each word cased as text (its description
    and its chapters' questions) writes it other than at the start of a sentence
    ("llm-knowledge-bases" -> "LLM knowledge bases", "amazon-dynamo" -> "Amazon Dynamo")."""
    words = []
    for w in tag.split('-'):
        cased = [m.group(1) for m in re.finditer(rf'(?<![\w-])({re.escape(w)})s?(?![\w-])', text or '', re.I)
                 if m.group(1) != w and not re.search(r'(?:\A|[.!?:]\s+)\Z', (text or '')[:m.start()])]
        words.append(cased[0] if cased else w)
    words[0] = words[0][0].upper() + words[0][1:]
    return ' '.join(words)


def _link(book, slug):
    text = book.chapters[slug].question.replace('[', '\\[').replace(']', '\\]')
    return f'[{text}](#{chapter_label(slug)})'


def _toctree(entries):
    """Sphinx's structure, hidden: a single-file book would put the pages it lists in its place,
    so the contents and the parts' maps are lists of links instead."""
    return '```{toctree}\n:hidden:\n\n' + ''.join(f'{e}\n' for e in entries) + '```\n'


LEVELS = ('Volume {n}: {title}', 'Chapter {n}: {title}', '{n} {title}')  # a part's title with its number, by depth


def part_title(book, part, pack=None):
    """A part's title; with pack, numbered as its level has it ("Chapter 1.2: Leaf a")."""
    words = ' '.join([part.description] + [book.chapters[c].question for c in part.chapters + part.see_also])
    plain = _escape(title(part.tag, words))
    return pack.t(LEVELS[part.depth]).replace('{n}', part.number).replace('{title}', plain) if pack else plain


def summary(text):
    """A chapter's first paragraph of its Abstract, for skimming; '' without one."""
    paras = [p for p in metadata.abstract(text).split('\n\n') if p and not re.match(r'\([^()\s]+\)=\Z', p)]
    return paras[0] if paras else ''


def _map(book, part, depth=0, summaries=None, minutes=None, pack=None):
    """A part's chapters and sections as a list of links, each section with its own; with
    summaries ({slug: text}), each chapter's after its link and each section's description,
    so a part page can be skimmed."""
    pad = '  ' * depth

    def after(text):
        return f' <span class="summary">— {text}</span>' if summaries is not None and text else ''
    out = ''.join(f'{pad}- {_link(book, c)}{" · " + minutes[c] if minutes and c in minutes else ""}{after((summaries or {}).get(c))}\n'
                  for c in part.chapters)
    for s in part.sections:
        out += (f'{pad}- [{part_title(book, s, pack)}](#{part_label(s.tag)}){after(_escape(s.description))}\n'
                + _map(book, s, depth + 1, summaries, minutes, pack))
    return out


def book_title(name):
    """The book's title, with sllmwiki's braces: {mengjia-sllmwiki 📖}."""
    return f'{{{_escape(name)} {TITLE_MARK}}}'


def head(book, name, trail, pack):
    """The line above a page's title: where it is, the book (to its cover) › each part above
    it (trail, outermost first, as Parts), and the contents at the right."""
    crumbs = ' › '.join([f'[{book_title(name)}](#{COVER})'] + [f'[{part_title(book, p)}](#{part_label(p.tag)})' for p in trail])
    return (f'<div class="headnote">\n\n<span class="crumbs">{crumbs}</span> '
            f'<span class="to-contents">[{pack.t("Contents")}](#{CONTENTS})</span>\n\n</div>\n\n')


ENDMARK = f'\n<div class="endmark">\n\n[sllmwiki]({layout.SKILL_URL})\n\n</div>\n'  # the quiet credit closing a chapter


def web_url(remote):
    """A git remote as the web page of its repository, or None: 'git@github.com:o/r.git',
    an SSH alias such as 'git@github-me:o/r', 'ssh://git@host/o/r' and 'https://user:token@host/o/r.git'
    all become 'https://<host>/o/r' (an alias naming GitHub is github.com); credentials never stay."""
    remote = (remote or '').strip()
    m = (re.match(r'(?:ssh://)?[^@/\s]+@([^:/\s]+)[:/](.+?)(?:\.git)?/?\Z', remote)
         or re.match(r'https?://(?:[^@/\s]+@)?([^/\s]+)/(.+?)(?:\.git)?/?\Z', remote))
    if not m or '/' not in m.group(2):
        return None
    host = 'github.com' if 'github' in m.group(1) and not m.group(1).endswith('.com') else m.group(1)
    return f'https://{host}/{m.group(2)}'


def model_names(ids):
    """Models as people read them: 'claude-opus-5-5' -> 'Claude Opus 5.5'; others as recorded."""
    out = []
    for i in ids:
        m = re.match(r'claude-([a-z]+)-([0-9]+)(?:-([0-9]+))?\Z', i)
        out.append(f'Claude {m.group(1).capitalize()} {m.group(2)}{"." + m.group(3) if m.group(3) else ""}' if m else i)
    return list(dict.fromkeys(out))


def contents(book, pack, appendices):
    """The contents: each part with its sections and chapters, then the appendices (labels and titles)."""
    out = ''
    for p in book.parts:
        out += f'- [{part_title(book, p, pack)}](#{part_label(p.tag)})\n' + _map(book, p, 1, pack=pack)
    return out + ''.join(f'- [{pack.t(t)}](#{label})\n' for label, t in appendices)


def cover(name, version, date, commit, pack, entries, listing, source=None, models=()):
    """index.md: the cover (with what made the book, from which wiki), the front page (design §9)
    and the contents (listing)."""
    meta = ' · '.join(f'**{pack.t(k)}:** {v}' for k, v in (('Version', version), ('Date', date), ('Commit', f'`{commit}`' if commit else '')) if v)
    marks = ''.join(f'- **{m}**: {pack.t(d)}\n' for m, d in markers.MARKERS.items())
    made = pack.t(MADE[0] if models else MADE[1]).replace('{tool}', f'[sllmwiki]({layout.SKILL_URL})').replace(
        '{models}', ', '.join(models)).replace('{source}', f'[{_escape(name)}]({source})' if source else _escape(name))
    return (f'({COVER})=\n# {book_title(name)}\n\n*{made}*\n\n{meta}\n\n({ABOUT})=\n## {pack.t("About this book")}\n\n'
            f'{" ".join(pack.t(t) for t in FRONT)}\n\n{pack.t(CITING)}\n\n{marks}\n'
            f'({CONTENTS})=\n## {pack.t("Contents")}\n\n{listing}\n' + _toctree(entries))


def part_page(book, part, pack, summaries=None, minutes=None):
    """parts/<tag>.md: the tag's title and description, a map of its chapters (with their
    summaries) and sections, and its see-also."""
    text = f'({part_label(part.tag)})=\n# {part_title(book, part, pack)}\n\n{_escape(part.description)}\n\n'
    entries = [f'../chapters/{c}' for c in part.chapters] + [s.tag for s in part.sections]
    if entries:
        text += _map(book, part, 0, summaries or {}, minutes, pack) + '\n' + _toctree(entries) + '\n'
    if part.see_also:
        text += f'**{pack.t("See also")}:** ' + ', '.join(_link(book, c) for c in part.see_also) + '\n'
    return text.rstrip('\n') + '\n'


def sources_page(book, sources, linked_by, pack):
    """Appendix A: each source a chapter links to, its abstract, license, date, link and the chapters citing it."""
    out = [f'({APPENDICES[0][0]})=\n# {pack.t(APPENDICES[0][1])}\n']
    for slug in sorted(linked_by):
        e = sources[slug]
        rows = [(pack.t('License'), e.get('license')), (pack.t('Published'), e.get('published')),
                (pack.t('Original'), f'<{e["url"]}>' if e.get('url') else None),
                (pack.t('Cited by'), ', '.join(_link(book, c) for c in linked_by[slug]))]
        out.append(f'({source_label(slug)})=\n## {slug}\n\n{_escape(e.get("abstract"))}\n\n'
                   + ''.join(f'- **{k}:** {v}\n' for k, v in rows if v))
    return '\n'.join(out)


def terms(text):
    """[(term, definition)] from a chapter's Terminology table, the markers' and readers' annotations' rows aside."""
    span = numbering.section(text, 'Terminology')
    rows = [line for line in text.split('\n')[span[0]:span[1]] if line.lstrip().startswith('|')] if span else []
    out = []
    for line in rows[2:]:  # the header and its rule
        cells = _cells(line.strip() if line.strip().endswith('|') else line.strip() + '|')
        if len(cells) >= 2 and cells[0].strip('*') not in markers.MARKERS and cells[0] != f'**{annotations.TERM}**':
            out.append((cells[0], ' | '.join(cells[1:])))
    return out


def glossary_page(book, texts, pack):
    """Appendix B: every term, A to Z; a definition several chapters share is listed once with all of them."""
    found = {}
    for slug in book.order():
        for term, definition in terms(texts[slug]):
            key = term.strip('*').strip().casefold()
            found.setdefault(key, {'term': term, 'defs': {}})['defs'].setdefault(definition, []).append(slug)
    if not found:
        return None
    rows = ''.join(f'| {v["term"]} | {d} ({", ".join(_link(book, c) for c in chapters)}) |\n'
                   for _, v in sorted(found.items()) for d, chapters in v['defs'].items())
    return (f'({APPENDICES[1][0]})=\n# {pack.t(APPENDICES[1][1])}\n\n'
            f'| {pack.t("Term")} | {pack.t("Definition")} |\n|---|---|\n{rows}')


def questions_page(book, texts, pack):
    """Appendix C: every statement or section marked [?], linked to its section."""
    items = []
    for slug in book.order():
        lines = texts[slug].split('\n')
        heads = numbering.headings(texts[slug])
        for i, col, marker in markers.uses(texts[slug]):
            if marker != '[?]':
                continue
            head = next((h for h in reversed(heads) if h.line <= i), None)
            label = lines[head.line - 1][1:-2] if head and head.line > 0 and lines[head.line - 1].endswith(')=') else chapter_label(slug)
            said = markers.unmark(head.title) if head and head.line == i else _cell(lines, i, col) or markers.statement(lines[i], col)
            items.append(f'- {said} ([{book.chapters[slug].question}](#{label}))\n')
    if not items:
        return None
    return f'({APPENDICES[2][0]})=\n# {pack.t(APPENDICES[2][1])}\n\n' + ''.join(items)


def _cells(line):
    """A table row's cells, split at the pipes outside code spans and not escaped."""
    cuts = [m.start() for m in _CELL.finditer(mask_code_spans(line))]
    return [line[a + 1:b].strip() for a, b in zip(cuts, cuts[1:])]


def _cell(lines, i, col):
    """For a marker in a table cell: "<row> (<column>): <cell>", else None."""
    if not lines[i].lstrip().startswith('|'):
        return None
    top = i
    while top > 0 and lines[top - 1].lstrip().startswith('|'):
        top -= 1
    at = len(_CELL.findall(mask_code_spans(lines[i])[:col])) - 1  # the pipes before it, less the leading one
    row, header = _cells(lines[i]), _cells(lines[top])
    if not 0 < at < min(len(row), len(header)):
        return None
    cell = re.sub(r'\s*\[\?\]\s*\Z', '', row[at])
    return f'{row[0].strip("*").strip()} ({header[at].strip("*").strip()}): {cell}'


def render_id(kind, source):
    """A diagram's or formula's id: the same source draws the same SVG."""
    return hashlib.md5(f'{kind}\n{source}'.encode()).hexdigest()[:16]


class Staged:
    """The staged book: {path: text} of its pages, the figures to copy (paths
    under the narratives folder), and book.json's content."""

    def __init__(self, files, figures, manifest):
        self.files, self.figures, self.manifest = files, figures, manifest


def stage(root, name, version, date, commit, source=None, title=None, author=None):
    """The book of the wiki at root as plain Markdown for Sphinx (design §6.2): name names its files, title (by
    default the name) is on its cover, author defaults to the title, and source is the wiki's URL."""
    title = title or name
    author = author or title
    b = model(root)
    pack = language.pack(config.get(root).settings['language']) or language.ENGLISH
    files, figures, problems, linked_by, texts = {}, [], list(b.problems), {}, {}
    parts = {s.tag: s for p in b.parts for s in p.walk()}
    parent = {c.tag: s for s in parts.values() for c in s.sections}

    def trail(tag):
        out = []
        while tag:
            out.insert(0, parts[tag])
            tag = parent[tag].tag if tag in parent else None
        return out
    for slug in b.order():
        r = rewrite(root, b, slug)
        texts[slug] = r.text
        files[f'chapters/{slug}.md'] = head(b, title, trail(b.part_of(b.chapters[slug].tag)), pack) + r.text.rstrip('\n') + '\n' + ENDMARK
        problems += r.problems
        figures += r.figures
        for s in r.sources:
            linked_by.setdefault(s, []).append(slug)
    summaries = {slug: summary(text) for slug, text in texts.items()}
    minutes = {slug: pack.t('{n} min').replace('{n}', str(metadata.reading(read_text(os.path.join(root, layout.NARRATIVES, f'{slug}.md')))[1]))
               for slug in texts}
    for tag, part in parts.items():
        files[f'parts/{tag}.md'] = head(b, title, trail(tag)[:-1], pack) + part_page(b, part, pack, summaries, minutes)
    pages = [(APPENDICES[0][2], sources_page(b, manifest.load(root, 'sources'), linked_by, pack) if linked_by else None),
             (APPENDICES[1][2], glossary_page(b, texts, pack)), (APPENDICES[2][2], questions_page(b, texts, pack))]
    for file, text in pages:
        if text:
            files[f'{file}.md'] = head(b, title, [], pack) + text
    made = [(label, t, file) for (label, t, file), (_, text) in zip(APPENDICES, pages) if text]
    recorded = manifest.load(root, 'narratives')
    models = model_names([m for slug in b.order() for m in (recorded[slug].get('models') or {}).values()])
    files['index.md'] = cover(title, version, date, commit, pack, [f'parts/{p.tag}' for p in b.parts] + [f for _, _, f in made],
                              contents(b, pack, [(label, t) for label, t, _ in made]), source, models)
    files = {path: without_comments(text) for path, text in files.items()}
    renders = {}
    for path, text in sorted(files.items()):
        for r in compat.renderables(text):
            entry = renders.setdefault(render_id(r.kind, r.source), {'kind': r.kind, 'source': r.source, 'files': []})
            if path not in entry['files']:
                entry['files'].append(path)
    anchors = sorted({line[1:-2] for t in files.values() for line in t.split('\n') if re.match(r'\([^()\s]+\)=\Z', line)})
    book_json = {'name': name, 'title': title, 'author': author, 'version': version, 'date': date, 'commit': commit, 'source': source, 'models': models,
                 'parts': [{'tag': s.tag, 'depth': s.depth, 'number': s.number, 'chapters': s.chapters} for p in b.parts for s in p.walk()],
                 'order': b.order(), 'anchors': anchors,
                 'renders': [dict(id=k, **v) for k, v in renders.items()],
                 'problems': [{'code': c, 'where': w, 'message': m} for c, w, m in problems]}
    return Staged(files, list(dict.fromkeys(figures)), book_json)


def check(root):
    """[(severity, code, file, message)] for wiki-check: what would break in the
    book although the wiki shows it. A link already broken in the wiki is left
    to the wiki's own checks (LINK_PATH, NARRATIVE_ANCHOR, CITATION_BROKEN)."""
    b = model(root)
    out = [('error', code, layout.NARRATIVES_MANIFEST, message) for code, _, message in b.problems]
    for slug in b.order():
        r = rewrite(root, b, slug)
        rel = f'{layout.NARRATIVES}/{slug}.md'
        for (code, where, message), dest in zip(r.problems, r.targets):
            if mdlinks.split(dest)[0] and mdlinks.problem(root, rel, dest):
                continue
            out.append(('error', code, where, f'{message}, in the book'))
    return out


def issues(data, pack=None):
    """The release notes' Known issues section for a built book's book.json: its problems,
    warnings and failed formats; '' when there are none."""
    pack = pack or language.ENGLISH
    lines = [f'- {f["code"]} {f["where"]}: {f["message"]}' for f in data.get('problems', []) + data.get('warnings', [])]
    lines += [f'- {fmt}: {why}' for fmt, why in (data.get('failed') or {}).items()]
    return f'### {pack.t("Known issues")}\n\n' + '\n'.join(lines) + '\n' if lines else ''
