#!/usr/bin/env python3
"""check-book: check a book the release action built (docs/book_execution_plan.md §2).

Usage: python3 check-book.py BOOK.html [--book STAGED/book.json] [--max-bytes N]
                             [--max-seconds N --seconds S]
                             [--pdf BOOK.pdf [--min-pages N] [--max-pages N]]
                             [--epub BOOK.epub --epubcheck EPUBCHECK.jar] [--json]

What it checks, in the single-file HTML:
  LINK_UNRESOLVED  a link within the book (href="#...") whose target id isn't there
  ID_DUPLICATE     an id used twice, so a link could land on the wrong one
  UNRENDERED       a diagram or formula left as code: a mermaid or math code
                   block, or a formula MathJax couldn't read
  SCRIPT           a <script>: the book must read with JavaScript off
  REMOTE           a stylesheet, image or other resource fetched from the
                   network (links to the original sources are fine)
  SIZE, TIME       the file over --max-bytes, the build over --max-seconds
With --pdf, the PDF Chrome printed from that HTML (poppler's pdfinfo, pdffonts and
pdftotext, from poppler-utils):
  PDF_PAGES        a page count outside --min-pages..--max-pages
  PDF_FONT         a font not embedded, so the PDF looks different elsewhere
  PDF_TEXT         a chapter's title missing from the PDF's text: glyphs that
                   don't extract (empty boxes for Chinese, say)
With --epub, the EPUB, by the W3C's epubcheck (java -jar EPUBCHECK.jar):
  EPUB_ERROR       an error or fatal error epubcheck reports
And, with --book, against what staging recorded:
  SVG_COUNT        fewer drawn diagrams and formulas than book.json lists
  BOOK_PROBLEM     a problem or warning book.json records (BOOK_LINK,
                   BOOK_RENDER, BOOK_SPHINX, ...)

CI runs it on the fixture wiki's book (.github/workflows/check-book.yml). It
reports; it never edits. Exit code: 0 = fine, 1 = findings, 2 = usage error.
"""

import argparse
import html.parser
import json
import os
import re
import subprocess
import sys


class _Scan(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.remote, self.scripts, self.svgs, self.code = [], [], [], 0, 0, []
        self.titles, self._title = [], None  # chapters' titles: a chapter's section is ch-<slug>

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.append(a['id'])
        if tag == 'section' and (a.get('id') or '').startswith('ch-') and self._title is None:
            self._title = 'next'
        elif self._title == 'next' and re.match(r'h[1-6]\Z', tag):
            self._title = []
        href = a.get('href') or ''
        if href.startswith('#'):
            self.links.append(href[1:])
        if tag == 'script':
            self.scripts += 1
        for attr in ('src', 'srcset', 'poster', 'data') + (('href',) if tag == 'link' else ()):
            if re.match(r'(?:https?:)?//', a.get(attr) or ''):
                self.remote.append(f'<{tag} {attr}="{a[attr]}">')
        if tag == 'svg' and a.get('role') == 'img':
            self.svgs += 1
        classes = (a.get('class') or '').split()
        if any(c in ('highlight-mermaid', 'highlight-math', 'language-mermaid', 'language-math') for c in classes) or 'data-mjx-error' in a:
            self.code.append(f'<{tag} class="{a.get("class", "")}">')
        if tag == 'a' and isinstance(self._title, list):  # a heading's ¶ link ends its title
            self.titles.append(''.join(self._title).strip())
            self._title = None

    def handle_data(self, data):
        if isinstance(self._title, list):
            self._title.append(data)

    def handle_endtag(self, tag):
        if isinstance(self._title, list) and re.match(r'h[1-6]\Z', tag):
            self.titles.append(''.join(self._title).strip())
            self._title = None


def check(text, book=None, max_bytes=None, seconds=None, max_seconds=None):
    """[(code, message)] for a built book's HTML text, and book.json's content when given."""
    scan = _Scan()
    scan.feed(text)
    ids, out = set(scan.ids), []
    for target in sorted({t for t in scan.links if t not in ids}):
        out.append(('LINK_UNRESOLVED', f'#{target}: no element has this id'))
    for i in sorted({i for i in scan.ids if scan.ids.count(i) > 1}):
        out.append(('ID_DUPLICATE', f'id "{i}" is used {scan.ids.count(i)} times'))
    for c in scan.code:
        out.append(('UNRENDERED', f'{c}: left as code'))
    if scan.scripts:
        out.append(('SCRIPT', f'{scan.scripts} <script> element(s)'))
    for r in scan.remote:
        out.append(('REMOTE', f'{r}: fetched from the network'))
    size = len(text.encode('utf-8'))
    if max_bytes is not None and size > max_bytes:
        out.append(('SIZE', f'{size:,} bytes, over {max_bytes:,}'))
    if max_seconds is not None and seconds is not None and seconds > max_seconds:
        out.append(('TIME', f'built in {seconds} s, over {max_seconds} s'))
    if book is not None:
        if scan.svgs < len(book.get('renders', [])):
            out.append(('SVG_COUNT', f'{scan.svgs} drawn, but book.json lists {len(book["renders"])} diagrams and formulas'))
        for f in book.get('problems', []) + book.get('warnings', []):
            out.append(('BOOK_PROBLEM', f'{f["code"]} {f["where"]}: {f["message"]}'))
    return out


def _tool(name, *args):
    p = subprocess.run([name, *args], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f'{name} failed: {(p.stderr or p.stdout).strip()}')
    return p.stdout


def check_pdf(pdf, titles, min_pages=None, max_pages=None):
    """[(code, message)] for the PDF printed from a book whose chapters have these titles."""
    out = []
    pages = int(re.search(r'^Pages:\s+(\d+)', _tool('pdfinfo', pdf), re.M).group(1))
    if (min_pages is not None and pages < min_pages) or (max_pages is not None and pages > max_pages):
        out.append(('PDF_PAGES', f'{pages} pages, outside {min_pages or 0}..{max_pages or "any"}'))
    for line in _tool('pdffonts', pdf).split('\n')[2:]:
        cols = line.split()
        # name type [encoding] emb sub uni object generation: emb is the fifth column from the end
        if len(cols) >= 7 and cols[-5] != 'yes':
            out.append(('PDF_FONT', f'{cols[0]} isn\'t embedded'))
    text = re.sub(r'\s+', '', _tool('pdftotext', '-enc', 'UTF-8', pdf, '-'))
    for t in titles:
        if re.sub(r'\s+', '', t) not in text:
            out.append(('PDF_TEXT', f'"{t}" isn\'t in the PDF\'s text'))
    return out


def check_epub(epub, jar):
    """[(code, message)] for each error or fatal error epubcheck reports on the EPUB."""
    p = subprocess.run(['java', '-jar', jar, epub, '--json', '-'], capture_output=True, text=True)
    start = re.search(r'^\{', p.stdout, re.M)  # epubcheck writes a line or two of text before its JSON
    try:
        report = json.loads(p.stdout[start.start():] if start else p.stdout)
    except ValueError:
        raise RuntimeError(f'epubcheck gave no report: {(p.stderr or p.stdout).strip()[-300:]}') from None
    out = []
    for m in report.get('messages', []):
        if m.get('severity') in ('ERROR', 'FATAL'):
            where = (m.get('locations') or [{}])[0]
            out.append(('EPUB_ERROR', f'{m.get("ID")} {where.get("path", "")}:{where.get("line", "")}: {m.get("message")}'))
    return out


def main(argv):
    p = argparse.ArgumentParser(prog='check-book.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('html')
    p.add_argument('--book')
    p.add_argument('--max-bytes', type=int)
    p.add_argument('--seconds', type=int)
    p.add_argument('--max-seconds', type=int)
    p.add_argument('--pdf')
    p.add_argument('--min-pages', type=int)
    p.add_argument('--max-pages', type=int)
    p.add_argument('--epub')
    p.add_argument('--epubcheck')
    p.add_argument('--json', action='store_true')
    args = p.parse_args(argv)
    if args.epub and not args.epubcheck:
        print('check-book.py: --epub needs --epubcheck EPUBCHECK.jar', file=sys.stderr)
        return 2
    for path in [args.html] + [f for f in (args.book, args.pdf, args.epub, args.epubcheck) if f]:
        if not os.path.isfile(path):
            print(f'check-book.py: no file {path}', file=sys.stderr)
            return 2
    with open(args.html, encoding='utf-8') as f:
        text = f.read()
    book = None
    if args.book:
        with open(args.book, encoding='utf-8') as f:
            book = json.load(f)
    found = check(text, book, args.max_bytes, args.seconds, args.max_seconds)
    if args.pdf:
        scan = _Scan()
        scan.feed(text)
        try:
            found += check_pdf(args.pdf, scan.titles, args.min_pages, args.max_pages)
        except (OSError, RuntimeError) as e:
            print(f'check-book.py: checking the PDF needs poppler-utils (pdfinfo, pdffonts, pdftotext): {e}', file=sys.stderr)
            return 2
    if args.epub:
        try:
            found += check_epub(args.epub, args.epubcheck)
        except (OSError, RuntimeError) as e:
            print(f'check-book.py: checking the EPUB needs Java and epubcheck: {e}', file=sys.stderr)
            return 2
    if args.json:
        print(json.dumps({'errors': len(found), 'findings': [{'code': c, 'message': m} for c, m in found]}, indent=2, ensure_ascii=False))
    else:
        for code, msg in found:
            print(f'error  {code:<16} {msg}')
        print(f'check-book: {len(found)} error(s) in {args.html} ({len(text.encode("utf-8")):,} bytes)')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
