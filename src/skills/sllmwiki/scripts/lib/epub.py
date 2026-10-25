"""An EPUB book as markdown (design doc §4.3).

  read(data) -> Book;  markdown(book) -> text;  slices(book, text) -> [(title, fragment, markdown)]

An EPUB is a zip of XHTML chapters. The book's own reading order (the
package's spine) gives the chapters, each converted like an HTML page
(lib/html2md.py), its headings moved down so its top one is a `##`, under the
book's title as the `#`. A chapter without a heading gets the title its table
of contents gives it (EPUB 3's navigation document, or EPUB 2's NCX). Links
within the book keep only their text, as they mean nothing in a saved copy, and
images their alt text. A book over SLICE_WORDS words is cut into slices, like a
long PDF: one per top-level entry of its contents, an entry still over
SLICE_WORDS cut by the entries under it, run together up to SLICE_WORDS
(Moby-Dick in runs of chapters, not as one "Moby Dick"), front and back matter
joining their neighbour; each is found again by its #chapter=N.

A book whose chapters are encrypted (DRM) is refused, never decrypted;
fonts obfuscated as the EPUB standard allows are not encryption of the text.
"""

import io
import posixpath
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

from . import html2md

SLICE_WORDS = 40000  # about what a PDF of SLICE_PAGES (100) pages holds
SLICE_MIN_WORDS = 500  # front or back matter shorter than this joins its neighbour
FONT_OBFUSCATION = ('http://www.idpf.org/2008/embedding', 'http://ns.adobe.com/pdf/enc#RC')
_LINK = re.compile(r'\[((?:\\.|[^\]\\])*)\]\(<([^>]*)>\)')  # html2md writes every link and image as [text](<href>)
_SCHEME = re.compile(r'[a-zA-Z][a-zA-Z0-9+.-]*:')


class EpubError(Exception):
    pass


class Book:
    def __init__(self, title, chapters, toc):
        self.title = title
        self.chapters = chapters  # [(path in the zip, XHTML text)], in reading order
        self.toc = toc  # [(depth, title, path, fragment)], depth 0 at the top


def _xml(data, what):
    try:
        return ET.fromstring(data)
    except ET.ParseError as e:
        raise EpubError(f'a broken EPUB: {what} isn\'t XML ({e})') from None


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def _all(node, name):
    return [n for n in node.iter() if _local(n.tag) == name]


def _text(node):
    return re.sub(r'\s+', ' ', ''.join(node.itertext())).strip()


def _resolve(base, href):
    """(path in the zip, fragment) of href, relative to the file at base."""
    path, _, frag = href.partition('#')
    path = urllib.parse.unquote(path)
    return (posixpath.normpath(posixpath.join(posixpath.dirname(base), path)) if path else base), frag


def _toc_nav(nav, base):
    """[(depth, title, path, fragment)] from an EPUB 3 navigation document's toc."""
    root = _xml(nav, 'its navigation document')
    navs = [n for n in _all(root, 'nav') if any(v.endswith('type') and 'toc' in val.split() for v, val in n.attrib.items())]
    out = []

    def walk(ol, depth):
        for li in [c for c in ol if _local(c.tag) == 'li']:
            label = next((c for c in li if _local(c.tag) in ('a', 'span')), None)
            href = label.get('href') if label is not None else None
            if label is not None and href:
                out.append((depth, _text(label), *_resolve(base, href)))
            for sub in [c for c in li if _local(c.tag) == 'ol']:
                walk(sub, depth + 1)
    for ol in [c for c in (navs[0] if navs else root).iter() if _local(c.tag) == 'ol'][:1]:
        walk(ol, 0)
    return out


def _toc_ncx(ncx, base):
    """[(depth, title, path, fragment)] from an EPUB 2 NCX."""
    root = _xml(ncx, 'its NCX')
    out = []

    def walk(node, depth):
        for point in [c for c in node if _local(c.tag) == 'navPoint']:
            label = next(iter(_all(point, 'text')), None)
            content = next((c for c in point if _local(c.tag) == 'content'), None)
            if label is not None and content is not None and content.get('src'):
                out.append((depth, _text(label), *_resolve(base, content.get('src'))))
            walk(point, depth + 1)
    for nav_map in _all(root, 'navMap')[:1]:
        walk(nav_map, 0)
    return out


def read(data):
    """The Book in an EPUB's bytes; raises EpubError for a broken or encrypted one."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        names = set(z.namelist())
    except zipfile.BadZipFile:
        raise EpubError('a broken EPUB: not a zip archive') from None

    def get(path):
        if path not in names:
            raise EpubError(f'a broken EPUB: no {path}')
        return z.read(path)
    container = _xml(get('META-INF/container.xml'), 'META-INF/container.xml')
    rootfile = next((r.get('full-path') for r in _all(container, 'rootfile') if r.get('full-path')), None)
    if not rootfile:
        raise EpubError('a broken EPUB: its container names no package')
    opf = _xml(get(rootfile), rootfile)
    items = {}
    for item in _all(opf, 'item'):
        if item.get('id') and item.get('href'):
            items[item.get('id')] = (_resolve(rootfile, item.get('href'))[0], item.get('media-type', ''), item.get('properties', ''))
    spine = [items[i.get('idref')][0] for i in _all(opf, 'itemref')
             if i.get('idref') in items and i.get('linear', 'yes') != 'no' and 'html' in items[i.get('idref')][1]]
    if not spine:
        raise EpubError('a broken EPUB: its spine lists no chapters')
    if 'META-INF/encryption.xml' in names:
        enc = _xml(z.read('META-INF/encryption.xml'), 'META-INF/encryption.xml')
        locked = set()
        for data_node in _all(enc, 'EncryptedData'):
            method = next((m.get('Algorithm') for m in _all(data_node, 'EncryptionMethod')), '')
            uri = next((r.get('URI') for r in _all(data_node, 'CipherReference')), '')
            if method not in FONT_OBFUSCATION and uri:
                locked.add(posixpath.normpath(urllib.parse.unquote(uri)))
        if locked & set(spine):
            raise EpubError('its chapters are encrypted (DRM); never get around it')
    title = next((_text(t) for t in _all(opf, 'title') if _text(t)), '')
    nav = next((p for p, _, props in items.values() if 'nav' in props.split()), None)
    ncx = next((p for p, media, _ in items.values() if media == 'application/x-dtbncx+xml'), None)
    toc = _toc_nav(get(nav), nav) if nav else _toc_ncx(get(ncx), ncx) if ncx else []
    chapters = [(p, get(p).decode('utf-8', 'replace')) for p in spine]
    return Book(title, chapters, toc)


def _shift(text, top):
    """text with its headings moved so the highest is level top, none past 6, outside code."""
    lines, fence, levels = text.split('\n'), None, []
    for line in lines:
        m = re.match(r'(`{3,}|~{3,})', line)
        if m and (fence is None or line.startswith(fence)):
            fence = None if fence else m.group(1)
        elif fence is None and re.match(r'#{1,6} ', line):
            levels.append(len(line) - len(line.lstrip('#')))
    if not levels:
        return text, False
    shift, fence, out = top - min(levels), None, []
    for line in lines:
        m = re.match(r'(`{3,}|~{3,})', line)
        if m and (fence is None or line.startswith(fence)):
            fence = None if fence else m.group(1)
        elif fence is None and re.match(r'#{1,6} ', line):
            hashes = len(line) - len(line.lstrip('#'))
            line = '#' * max(1, min(6, hashes + shift)) + line[hashes:]
        out.append(line)
    return '\n'.join(out), True


def _unlink(text):
    """text with links to places in the book reduced to their text, and images to their alt text."""
    def one(m):
        label, href = m.groups()
        if _SCHEME.match(href):
            return m.group(0)
        return f'\\[{label}\\]' if label.startswith('image: ') else label
    return _LINK.sub(one, text)


def chapter_markdown(book):
    """[(path, markdown)] of each chapter, its top heading a ## for a top-level entry of the contents, ### one level down."""
    entries = {}
    for depth, title, path, _ in book.toc:
        entries.setdefault(path, (depth, title))
    out = []
    for path, page in book.chapters:
        depth, title = entries.get(path, (0, ''))
        text = _unlink(html2md.body(page)).strip()
        text, headed = _shift(text, min(6, 2 + depth))
        if not headed and title:
            text = f'{"#" * min(6, 2 + depth)} {title}\n\n{text}' if text else ''
        if text.strip():
            out.append((path, text.strip()))
    return out


def markdown(book):
    """The whole book as markdown: its title, then each chapter in reading order."""
    head = f'# {book.title}\n\n' if book.title else ''
    return head + '\n\n'.join(t for _, t in chapter_markdown(book)) + '\n'


def _groups(chapters, starts, lead):
    """[[title, [path, ...], start]]: the chapters cut where a start (path -> title) begins, or where the pages that
    lead into it begin (lead: path -> the cut entry whose own pages open it); what comes first opens the first."""
    begin = {}
    for start in starts:
        at = start
        while at in lead:
            at = lead[at]
        begin[at] = start
    groups = []
    for path, _ in chapters:
        if path in begin or not groups:
            groups.append([starts.get(begin.get(path)), [], begin.get(path)])
        groups[-1][1].append(path)
    if len(groups) > 1 and groups[0][2] is None:
        front = groups.pop(0)  # popped first: the next group is then groups[0]
        groups[0][1][:0] = front[1]
    return groups


def slices(book, text):
    """[(title, 'chapter=N', markdown)] for a book over SLICE_WORDS words: one per top-level entry of its contents, an
    entry still over SLICE_WORDS cut by the entries under it, run together up to SLICE_WORDS, and front or back matter
    under SLICE_MIN_WORDS joining its neighbour."""
    if len(text.split()) <= SLICE_WORDS:
        return []
    chapters = chapter_markdown(book)
    words = {path: len(md.split()) for path, md in chapters}
    entries = [(d, t, p) for d, t, p, _ in book.toc if p in words]
    starts, lead, parent = {}, {}, {}  # path -> title; first entry under a cut one -> it; entry -> the one it was cut from
    for depth, title, path in entries:
        if depth == 0:
            starts.setdefault(path, title)
    size = lambda paths: sum(words[p] for p in paths)  # noqa: E731
    while True:
        cut = False
        for _, paths, start in _groups(chapters, starts, lead):
            if start is None or size(paths) <= SLICE_WORDS:
                continue
            at = next(n for n, e in enumerate(entries) if e[2] == start)
            under = []
            for depth, sub, path in entries[at + 1:]:
                if depth <= entries[at][0]:
                    break
                if depth == entries[at][0] + 1 and path in paths and path not in starts:
                    under.append((path, sub))
            if under:
                del starts[start]
                starts.update(under)
                lead[under[0][0]] = start  # its own pages (a half-title) open the first entry under it
                parent.update((path, start) for path, _ in under)
                cut = True
        if not cut:
            break
    packed = []  # entries cut from the same one, run together up to SLICE_WORDS: Moby-Dick in a few slices, not 135
    for title, paths, start in _groups(chapters, starts, lead):
        last = packed[-1] if packed else None
        if last and parent.get(start) is not None and parent.get(start) == parent.get(last[2]) and size(last[1] + paths) <= SLICE_WORDS:
            last[1].extend(paths)
            last[3] = title
        else:
            packed.append([title, list(paths), start, title])
    groups = [[first if first == final else f'{first} – {final}', paths] for first, paths, _, final in packed]
    while len(groups) > 1 and size(groups[0][1]) < SLICE_MIN_WORDS:
        front = groups.pop(0)
        groups[0][1][:0] = front[1]
    while len(groups) > 1 and size(groups[-1][1]) < SLICE_MIN_WORDS:
        back = groups.pop()
        groups[-1][1].extend(back[1])
    if len(groups) < 2:
        return []
    text_of = dict(chapters)
    return [(title, f'chapter={n}', '\n\n'.join(text_of[p] for p in paths) + '\n') for n, (title, paths) in enumerate(groups, 1)]
