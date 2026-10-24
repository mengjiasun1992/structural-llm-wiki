#!/usr/bin/env python3
"""check-book: check a book the release action built (docs/book_execution_plan.md §2).

Usage: python3 check-book.py BOOK.html [--book STAGED/book.json] [--max-bytes N]
                             [--max-seconds N --seconds S] [--json]

What it checks, in the single-file HTML:
  LINK_UNRESOLVED  a link within the book (href="#...") whose target id isn't there
  ID_DUPLICATE     an id used twice, so a link could land on the wrong one
  UNRENDERED       a diagram or formula left as code: a mermaid or math code
                   block, or a formula MathJax couldn't read
  SCRIPT           a <script>: the book must read with JavaScript off
  REMOTE           a stylesheet, image or other resource fetched from the
                   network (links to the original sources are fine)
  SIZE, TIME       the file over --max-bytes, the build over --max-seconds
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
import sys


class _Scan(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.remote, self.scripts, self.svgs, self.code = [], [], [], 0, 0, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.append(a['id'])
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


def main(argv):
    p = argparse.ArgumentParser(prog='check-book.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('html')
    p.add_argument('--book')
    p.add_argument('--max-bytes', type=int)
    p.add_argument('--seconds', type=int)
    p.add_argument('--max-seconds', type=int)
    p.add_argument('--json', action='store_true')
    args = p.parse_args(argv)
    for path in [args.html] + ([args.book] if args.book else []):
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
    if args.json:
        print(json.dumps({'errors': len(found), 'findings': [{'code': c, 'message': m} for c, m in found]}, indent=2, ensure_ascii=False))
    else:
        for code, msg in found:
            print(f'error  {code:<16} {msg}')
        print(f'check-book: {len(found)} error(s) in {args.html} ({len(text.encode("utf-8")):,} bytes)')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
