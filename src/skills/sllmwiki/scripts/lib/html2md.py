"""An HTML page's main content as markdown (design doc §4.3).

The main content is the page's <main>, else its <article>, else its <body>;
navigation, headers, footers, sidebars, forms, scripts, comments and anything
hidden are left out. Headings, paragraphs, lists, block quotes, code, tables,
links, emphasis and line breaks are kept; images stay links to the original.
Math is kept as TeX, $...$ or $$...$$, from MathML's alttext or TeX annotation,
even where the page hides the MathML behind an image (as Wikipedia does).
Links are made absolute against the page's URL.
"""

import html.parser
import re
import urllib.parse

DROP = {'script', 'style', 'noscript', 'nav', 'header', 'footer', 'aside', 'form', 'iframe', 'svg', 'button', 'template',
        'select', 'input', 'textarea', 'canvas', 'object', 'embed', 'dialog'}
DROP_ROLES = {'navigation', 'banner', 'contentinfo', 'complementary', 'search', 'dialog'}
VOID = {'br', 'hr', 'img', 'meta', 'link', 'input', 'source', 'wbr', 'col', 'area', 'base', 'track', 'param'}
BLOCK = {'p', 'div', 'section', 'main', 'article', 'body', 'html', 'ul', 'ol', 'li', 'blockquote', 'pre', 'table', 'thead', 'tbody',
         'tfoot', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'dl', 'dt', 'dd', 'figure', 'figcaption', 'details', 'summary'}


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []


class _Tree(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root', [])
        self.cur = self.root
        self.title = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self._in_title = True
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or '') + data
        self.cur.children.append(data)


def _hidden(node):
    a = node.attrs
    return (node.tag in DROP or (a.get('role') or '').lower() in DROP_ROLES or 'hidden' in a
            or (a.get('aria-hidden') or '').lower() == 'true' or re.search(r'display:\s*none', a.get('style') or '') is not None)


def _find(node, tag):
    for c in node.children:
        if isinstance(c, Node) and not _hidden(c):
            if c.tag == tag:
                return c
            found = _find(c, tag)
            if found:
                return found
    return None


class _Writer:
    def __init__(self, base):
        self.base = base

    def url(self, href):
        href = (href or '').strip()
        if not href or href.lower().startswith(('javascript:', 'data:')):
            return None
        return urllib.parse.urljoin(self.base, href) if self.base else href

    def inline(self, node):
        """The node's content as one line of markdown."""
        out = []
        for c in node.children:
            if isinstance(c, str):
                out.append(_escape(re.sub(r'\s+', ' ', c)))
            elif _math_holder(c):
                out.append(_math(c))
            elif _hidden(c):
                continue
            elif c.tag == 'br':
                out.append('\\\n')  # a hard line break, in every CommonMark renderer
            elif c.tag == 'img':
                src = self.url(c.attrs.get('src'))
                if src:
                    out.append(f'[image: {_escape(c.attrs.get("alt") or "")}](<{src}>)')
            elif c.tag == 'a':
                text = self.inline(c).strip()
                raw = (c.attrs.get('href') or '').strip()
                href = None if raw.startswith('#') else self.url(raw)  # a link within the page means nothing in a saved copy
                out.append(f'[{text}](<{href}>)' if href and text else text)
            elif c.tag in ('code', 'kbd', 'samp', 'tt'):
                raw = re.sub(r'\s+', ' ', _text(c))
                fence = '``' if '`' in raw else '`'
                out.append(f'{fence}{raw}{fence}' if raw.strip() else '')
            elif c.tag in ('strong', 'b'):
                out.append(_wrap('**', self.inline(c)))
            elif c.tag in ('em', 'i', 'cite'):
                out.append(_wrap('*', self.inline(c)))
            elif c.tag in ('del', 's', 'strike'):
                out.append(_wrap('~~', self.inline(c)))
            else:
                out.append(self.inline(c))
        return re.sub(r' *(\\?\n) *', r'\1', re.sub(r'(?<=\S) {2,}', ' ', ''.join(out)))

    def blocks(self, node, depth=0):
        """The node's content as a list of markdown blocks (each a string)."""
        out, run = [], []

        def flush():
            text = ''.join(run).strip()
            if text:
                out.append(text)
            run.clear()

        for c in node.children:
            if isinstance(c, str) or (c.tag not in BLOCK and not _hidden(c)):
                holder = Node('span', [])
                holder.children = [c]
                run.append(self.inline(holder))
                continue
            if _hidden(c):
                continue
            flush()
            out += self.block(c, depth)
        flush()
        return out

    def block(self, c, depth):
        t = c.tag
        if t in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            text = self.inline(c).replace('\n', ' ').strip()
            return [f'{"#" * int(t[1])} {text}'] if text else []
        if t == 'hr':
            return ['---']
        if t == 'pre':
            code = _text(c).strip('\n')
            lang = next((cls[len(p):] for x in [c] + [k for k in c.children if isinstance(k, Node)]
                         for cls in (x.attrs.get('class') or '').split() for p in ('language-', 'lang-') if cls.startswith(p)), '')
            fence = '````' if '```' in code else '```'
            return [f'{fence}{lang}\n{code}\n{fence}']
        if t == 'blockquote':
            inner = '\n\n'.join(self.blocks(c, depth))
            return ['\n'.join('>' + (' ' + line if line else '') for line in inner.split('\n'))] if inner else []
        if t in ('ul', 'ol'):
            items, n = [], int(c.attrs.get('start') or 1) if t == 'ol' else 0
            for li in c.children:
                if not isinstance(li, Node) or li.tag != 'li' or _hidden(li):
                    continue
                marker = f'{n}. ' if t == 'ol' else '- '
                parts = self.blocks(li, depth + 1)
                body = ''.join((('\n' if re.match(r'(- |[0-9]+\. )', b) else '\n\n') if i else '') + b for i, b in enumerate(parts))
                pad = ' ' * len(marker)
                lines = body.split('\n')
                items.append(marker + lines[0] + ''.join('\n' + (pad + line if line else '') for line in lines[1:]))
                n += 1
            return ['\n'.join(items)] if items else []
        if t == 'table':
            return self.table(c)
        if t in ('dt', 'summary', 'figcaption'):
            text = self.inline(c).strip()
            return [f'**{text}**'] if text and t == 'dt' else [text] if text else []
        return self.blocks(c, depth)

    def table(self, node):
        rows = []

        def collect(n):
            for c in n.children:
                if isinstance(c, Node) and not _hidden(c):
                    if c.tag == 'tr':
                        rows.append([self.inline(cell).replace('\n', ' ').replace('|', '\\|').strip()
                                     for cell in c.children if isinstance(cell, Node) and cell.tag in ('td', 'th')])
                    elif c.tag != 'table':
                        collect(c)
        collect(node)
        rows = [r for r in rows if r]
        if not rows:
            return []
        width = max(len(r) for r in rows)
        rows = [r + [''] * (width - len(r)) for r in rows]
        lines = ['| ' + ' | '.join(rows[0]) + ' |', '|' + '---|' * width] + ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
        return ['\n'.join(lines)]


def _math_holder(node):
    """A <math> element, or a wrapper around one and its image fallback (MediaWiki's mwe-math-element)."""
    return node.tag == 'math' or 'mwe-math-element' in (node.attrs.get('class') or '').split()


def _descendant(node, tag):
    for c in node.children:
        if isinstance(c, Node):
            if c.tag == tag:
                return c
            found = _descendant(c, tag)
            if found:
                return found
    return None


def _math(node):
    """The formula in node as $TeX$, or $$TeX$$ for display math; its text when it has no TeX."""
    math = node if node.tag == 'math' else _descendant(node, 'math')
    if math is None:
        return ''
    annotation = next((a for a in _all(math, 'annotation') if 'tex' in (a.attrs.get('encoding') or '')), None)
    tex = (math.attrs.get('alttext') or (_text(annotation) if annotation else '')).strip()
    m = re.fullmatch(r'\{\\(?:displaystyle|textstyle)\s*(.*)\}', tex, re.S)
    tex = re.sub(r'\s+', ' ', m.group(1) if m else tex).strip()
    if not tex:
        return _escape(re.sub(r'\s+', ' ', _text(math)).strip())
    block = (math.attrs.get('display') == 'block' or 'mwe-math-element-block' in (node.attrs.get('class') or '').split())
    return f'$${tex}$$' if block else f'${tex}$'


def _all(node, tag):
    for c in node.children:
        if isinstance(c, Node):
            if c.tag == tag:
                yield c
            yield from _all(c, tag)


def _text(node):
    return ''.join(c if isinstance(c, str) else _text(c) for c in node.children)


def _wrap(mark, text):
    stripped = text.strip()
    return f'{mark}{stripped}{mark}' if stripped else text


def _escape(text):
    """Characters that would start markup in running text get a backslash."""
    return re.sub(r'([\\`*_\[\]<>])', r'\\\1', text)


def _parse(page, base_url):
    """(the main content's markdown, the page's <title>)."""
    tree = _Tree()
    tree.feed(page)
    tree.close()
    main = _find(tree.root, 'main') or _find(tree.root, 'article') or _find(tree.root, 'body') or tree.root
    blocks = _Writer(base_url).blocks(main)
    return '\n\n'.join(b for b in blocks if b.strip()), re.sub(r'\s+', ' ', tree.title or '').strip() or None


def body(page, base_url=None):
    """An HTML page's main content as markdown, without a title added: an EPUB's chapter, say."""
    return _parse(page, base_url)[0].strip() + '\n'


def convert(page, base_url=None):
    """(markdown, title) for an HTML page's main content."""
    text, title = _parse(page, base_url)
    if title and not re.match(r'# ', text):
        text = f'# {title}\n\n{text}' if text else f'# {title}'
    return text.strip() + '\n', title
