"""The wiki as a book (docs/book_design.md §5): its parts, its chapters in
teaching order, the sources each chapter cites, and each chapter rewritten for
the book (§5.3).

Parts follow the tag tree: a part per top-level tag, a section per child tag
under it, at any depth. A narrative is a chapter under its first primary tag
only; its other tags list it as see-also. Within a tag, chapters go in
teaching order (§5.2): after the narratives they're built on, then by
template, then by question.
"""

import hashlib
import heapq
import os
import posixpath
import re

from . import citations, compat, config, language, layout, manifest, markers, mdlinks, metadata, numbering, tagtree
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
    message) and the link each is about (targets), the sources it links to, and
    the figures it shows (paths under the narratives folder)."""

    def __init__(self, text, problems, sources, figures, targets=()):
        self.text, self.problems, self.sources, self.figures = text, problems, sources, figures
        self.targets = list(targets)


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
            if frag in own:
                return '#' + section_label(slug, frag)
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
            if frag not in _anchors(root, base):
                fail(dest, 'BOOK_LINK', where, f'{dest}: {base} has no section #{frag}')
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
    return Rewritten('\n'.join(lines), problems, list(dict.fromkeys(sources)), list(dict.fromkeys(figures)), targets)


def _without_metadata(text):
    """text without its Metadata section, which the book replaces by a version line."""
    span = numbering.section(text, 'Metadata')
    lines = text.split('\n')
    if span:
        del lines[span[0]:span[1]]
    return '\n'.join(lines).rstrip('\n') + '\n'


def _anchors(root, slug):
    return numbering.anchors(_without_metadata(read_text(os.path.join(root, layout.NARRATIVES, f'{slug}.md'))))


# The generated pages (design §5.1), their labels and files in the staged folder
COVER, ABOUT = 'book--cover', 'book--about'
APPENDICES = (('book--sources', 'Appendix A: Sources', 'appendix-sources'),
              ('book--glossary', 'Appendix B: Glossary', 'appendix-glossary'),
              ('book--questions', 'Appendix C: Open questions', 'appendix-questions'))
FRONT = ("The narratives in this book are the wiki owner's work. Every source belongs to its authors: "
         'the book links to it and quotes it briefly, but never copies it.',
         'The narratives were written by an LLM and reviewed by the owner.',
         'This book is a snapshot of the wiki at the commit on its cover.')
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


def part_title(book, part):
    words = ' '.join([part.description] + [book.chapters[c].question for c in part.chapters + part.see_also])
    return _escape(title(part.tag, words))


def _map(book, part, depth=0):
    """A part's chapters and sections as a list of links, each section with its own."""
    pad = '  ' * depth
    out = ''.join(f'{pad}- {_link(book, c)}\n' for c in part.chapters)
    for s in part.sections:
        out += f'{pad}- [{part_title(book, s)}](#{part_label(s.tag)})\n' + _map(book, s, depth + 1)
    return out


def contents(book, pack, appendices):
    """The contents: each part with its sections and chapters, then the appendices (labels and titles)."""
    out = ''
    for p in book.parts:
        out += f'- [{part_title(book, p)}](#{part_label(p.tag)})\n' + _map(book, p, 1)
    return out + ''.join(f'- [{pack.t(t)}](#{label})\n' for label, t in appendices)


def cover(name, version, date, commit, pack, entries, listing):
    """index.md: the cover, the front page (design §9) and the contents (listing)."""
    meta = ' · '.join(f'**{pack.t(k)}:** {v}' for k, v in (('Version', version), ('Date', date), ('Commit', f'`{commit}`' if commit else '')) if v)
    marks = ''.join(f'- **{m}**: {pack.t(d)}\n' for m, d in markers.MARKERS.items())
    return (f'({COVER})=\n# {_escape(name)}\n\n{meta}\n\n({ABOUT})=\n## {pack.t("About this book")}\n\n'
            f'{" ".join(pack.t(t) for t in FRONT)}\n\n{pack.t(CITING)}\n\n{marks}\n'
            f'({CONTENTS})=\n## {pack.t("Contents")}\n\n{listing}\n' + _toctree(entries))


def part_page(book, part, pack):
    """parts/<tag>.md: the tag's title and description, a map of its chapters and sections, and its see-also."""
    text = f'({part_label(part.tag)})=\n# {part_title(book, part)}\n\n{_escape(part.description)}\n\n'
    entries = [f'../chapters/{c}' for c in part.chapters] + [s.tag for s in part.sections]
    if entries:
        text += _map(book, part) + '\n' + _toctree(entries) + '\n'
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
    """[(term, definition)] from a chapter's Terminology table, the markers' rows aside."""
    span = numbering.section(text, 'Terminology')
    rows = [line for line in text.split('\n')[span[0]:span[1]] if line.lstrip().startswith('|')] if span else []
    out = []
    for line in rows[2:]:  # the header and its rule
        cells = _cells(line.strip() if line.strip().endswith('|') else line.strip() + '|')
        if len(cells) >= 2 and cells[0].strip('*') not in markers.MARKERS:
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


def stage(root, name, version, date, commit):
    """The book of the wiki at root as plain Markdown for Sphinx (design §6.2)."""
    b = model(root)
    pack = language.pack(config.get(root).settings['language']) or language.ENGLISH
    files, figures, problems, linked_by, texts = {}, [], list(b.problems), {}, {}
    for slug in b.order():
        r = rewrite(root, b, slug)
        texts[slug] = files[f'chapters/{slug}.md'] = r.text
        problems += r.problems
        figures += r.figures
        for s in r.sources:
            linked_by.setdefault(s, []).append(slug)
    for p in b.parts:
        for part in p.walk():
            files[f'parts/{part.tag}.md'] = part_page(b, part, pack)
    pages = [(APPENDICES[0][2], sources_page(b, manifest.load(root, 'sources'), linked_by, pack) if linked_by else None),
             (APPENDICES[1][2], glossary_page(b, texts, pack)), (APPENDICES[2][2], questions_page(b, texts, pack))]
    for file, text in pages:
        if text:
            files[f'{file}.md'] = text
    made = [(label, t, file) for (label, t, file), (_, text) in zip(APPENDICES, pages) if text]
    files['index.md'] = cover(name, version, date, commit, pack, [f'parts/{p.tag}' for p in b.parts] + [f for _, _, f in made],
                              contents(b, pack, [(label, t) for label, t, _ in made]))
    renders = {}
    for path, text in sorted(files.items()):
        for r in compat.renderables(text):
            entry = renders.setdefault(render_id(r.kind, r.source), {'kind': r.kind, 'source': r.source, 'files': []})
            if path not in entry['files']:
                entry['files'].append(path)
    anchors = sorted({line[1:-2] for t in files.values() for line in t.split('\n') if re.match(r'\([^()\s]+\)=\Z', line)})
    book_json = {'name': name, 'version': version, 'date': date, 'commit': commit,
                 'parts': [{'tag': s.tag, 'depth': s.depth, 'chapters': s.chapters} for p in b.parts for s in p.walk()],
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
