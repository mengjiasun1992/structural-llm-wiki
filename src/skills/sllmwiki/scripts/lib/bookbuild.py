"""Building the staged book (docs/book_design.md §6.3-§6.5): its diagrams and
math drawn as SVG in headless Chrome, the staged pages with the SVG put in,
and Sphinx's single-file HTML made self-contained.

Chrome renders every item on one page and is run with --dump-dom, so no
browser driver is needed: the page writes its results into a <textarea>,
read back from the dumped DOM.
"""

import base64
import hashlib
import html
import json
import mimetypes
import os
import posixpath
import re
import shutil
import subprocess
import zipfile
from xml.etree import ElementTree

from . import compat

MERMAID, MATHJAX = 'mermaid.min.js', 'tex-svg-full.js'  # the vendored libraries' file names
FONT = '"Noto Sans", "Noto Sans CJK SC", "Noto Sans Math", sans-serif'
CHROMES = ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser',
           '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
# Sphinx's names for the languages it translates its own labels into
SPHINX_LANGUAGES = {'zh-hans': 'zh_CN', 'zh-hant': 'zh_TW', 'pt-br': 'pt_BR'}

_PAGE = """<!doctype html><meta charset="utf-8">
<script>window.MathJax = {svg: {fontCache: 'none'}, startup: {typeset: false}};</script>
<script src="%(mathjax)s"></script>
<script src="%(mermaid)s"></script>
<textarea id="result"></textarea>
<script>
const items = %(items)s;
(async () => {
  const out = [];
  try {
    await MathJax.startup.promise;
    mermaid.initialize({startOnLoad: false, htmlLabels: false, flowchart: {htmlLabels: false},
                        securityLevel: 'strict', theme: 'default', fontFamily: %(font)s});
  } catch (e) { out.push({setup: String(e && e.message || e)}); }
  const ser = new XMLSerializer();
  for (const it of items) {
    try {
      if (it.kind === 'mermaid') {
        out.push({id: it.id, svg: (await mermaid.render('r' + it.id, it.source)).svg});
      } else {
        const node = await MathJax.tex2svgPromise(it.source, {display: it.kind === 'display'});
        const err = node.querySelector('[data-mjx-error]');
        out.push(err ? {id: it.id, error: err.getAttribute('data-mjx-error')}
                     : {id: it.id, svg: ser.serializeToString(node.querySelector('svg'))});
      }
    } catch (e) { out.push({id: it.id, error: String(e && e.message || e)}); }
  }
  document.getElementById('result').textContent = JSON.stringify(out);
})();
</script>
"""


def find_chrome(given=None):
    """The Chrome to run: given, else $CHROME, else the first of CHROMES found; None when there's none."""
    for c in [given, os.environ.get('CHROME')] + ([] if given else list(CHROMES)):
        if c and (os.path.isfile(c) or shutil.which(c)):
            return shutil.which(c) or c
    return None


def libraries(vendor):
    """A short hash of the vendored libraries, so a cached SVG is redrawn when they change."""
    h = hashlib.md5()
    for name in (MERMAID, MATHJAX):
        with open(os.path.join(vendor, name), 'rb') as f:
            h.update(f.read())
    return h.hexdigest()[:12]


def page(items, vendor):
    """The HTML page that draws items ([{id, kind, source}]) with the vendored libraries."""
    url = 'file://' + os.path.abspath(vendor).replace(os.sep, '/') + '/'
    return _PAGE % {'mathjax': url + MATHJAX, 'mermaid': url + MERMAID, 'font': json.dumps(FONT),
                    'items': json.dumps(items, ensure_ascii=False).replace('</', '<\\/')}


def results(dom):
    """{id: svg or {'error': message}} from the DOM Chrome dumped; raises ValueError when the page didn't finish."""
    m = re.search(r'<textarea id="result">(.*?)</textarea>', dom or '', re.S)
    if not m or not m.group(1).strip():
        raise ValueError('the render page wrote no results: did the libraries load?')
    out = {}
    for r in json.loads(html.unescape(m.group(1))):
        if 'setup' in r:
            raise ValueError(f'the libraries failed to start: {r["setup"]}')
        out[r['id']] = r['svg'] if 'svg' in r else {'error': r['error']}
    return out


def draw(items, vendor, chrome, workdir, timeout=600):
    """Run Chrome on page(items) in workdir; results() of what it dumped."""
    path = os.path.join(workdir, '_render.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(page(items, vendor))
    run = subprocess.run([chrome, '--headless', '--disable-gpu', '--no-sandbox', '--allow-file-access-from-files',
                          '--virtual-time-budget=60000', '--dump-dom', 'file://' + os.path.abspath(path).replace(os.sep, '/')],
                         capture_output=True, text=True, timeout=timeout, check=False)
    os.remove(path)
    return results(run.stdout)


def clean(svg, source):
    """An SVG made to stand alone and to be valid XML in HTML, print and EPUB:
    <br> closed, one line, every <rect> with the width and height SVG 1.1
    requires, no id twice, and the source as its accessible name."""
    svg = re.sub(r'<br\s*>', '<br/>', svg).replace('\r', '').replace('\n', ' ')

    def rect(m):
        tag = m.group(0)
        for attr in ('width', 'height'):
            if not re.search(rf'\s{attr}="', tag):
                tag = tag.replace('<rect', f'<rect {attr}="0"', 1)
        return tag
    svg = re.sub(r'<rect\b[^>]*>', rect, svg)
    seen = set()

    def once(m):  # mermaid's mindmap gives a node and its shape the same id
        value = m.group(1)
        while value in seen:
            value += '-x'
        seen.add(value)
        return f' id="{value}"'
    svg = re.sub(r'\sid="([^"]+)"', once, svg)
    head, rest = svg.split('>', 1)
    head = re.sub(r'\s(?:role|aria-label|aria-roledescription|aria-hidden)="[^"]*"', '', head)
    name = html.escape(source, quote=True).replace('\n', '&#10;')
    return f'{head} role="img" aria-label="{name}">{rest}'.replace('|', '&#124;')  # a | would split a table cell


def markup(kind, svg):
    """The HTML a staged page holds in place of a diagram or formula."""
    if kind == 'inline':
        return f'<span class="math">{svg}</span>'
    return f'<div class="{"diagram" if kind == "mermaid" else "math display"}">{svg}</div>'


def put_in(text, svgs, render_id, counts):
    """text with each diagram and formula that svgs ({id: svg}) has replaced by
    its markup; one drawn twice in the book gets its ids renamed (counts keeps
    how often each id was used), so no id repeats in a single-file book."""
    lines, found = text.split('\n'), []
    for r in compat.renderables(text):  # numbered in reading order, so the first keeps its ids
        rid = render_id(r.kind, r.source)
        if isinstance(svgs.get(rid), str):
            found.append((r, rid, counts.get(rid, 0)))
            counts[rid] = counts.get(rid, 0) + 1
    for r, rid, n in reversed(found):  # replaced from the end, so earlier positions stay put
        svg = svgs[rid].replace(f'r{rid}', f'r{rid}-{n}') if n else svgs[rid]
        html_ = markup(r.kind, svg)
        if r.kind == 'inline':
            lines[r.first] = lines[r.first][:r.start] + html_ + lines[r.first][r.end:]
        else:
            lines[r.first:r.last + 1] = ['', html_, '']
    return '\n'.join(lines)


def sphinx_language(tag):
    """Sphinx's language for a BCP 47 tag ('zh-Hans' -> 'zh_CN')."""
    return SPHINX_LANGUAGES.get((tag or 'en').lower(), (tag or 'en').replace('-', '_'))


def self_contained(folder):
    """Sphinx's singlehtml output in folder as one file's text: its stylesheets
    and images inlined; its scripts, search and navigation bars dropped; and
    the links it writes between documents, #document-<doc>#<id>, made #<id>."""
    with open(os.path.join(folder, 'index.html'), encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'href="#document-[^"#]*#', 'href="#', text)
    text = re.sub(r'<script\b[^>]*>.*?</script>\s*', '', text, flags=re.S)
    text = re.sub(r'<link rel="(?:index|search|next|prev)"[^>]*>\s*', '', text)
    text = re.sub(r'<div class="related" role="navigation".*?</div>\s*', '', text, flags=re.S)

    def css(m):
        with open(os.path.join(folder, m.group(1).split('?')[0]), encoding='utf-8') as f:
            return f'<style>\n{f.read()}\n</style>'
    text = re.sub(r'<link rel="stylesheet"[^>]*href="([^"]+)"[^>]*/?>', css, text)

    def image(m):
        path = os.path.join(folder, html.unescape(m.group(2)))
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        return f'{m.group(1)}data:{mimetypes.guess_type(path)[0] or "application/octet-stream"};base64,{data}"'
    return re.sub(r'(<img\b[^>]*\bsrc=")(?!data:|[a-z]+://)([^"]+)"', image, text)


def print_pdf(html_path, pdf_path, chrome, title, timeout=600):
    """Chrome prints the single-file HTML to pdf_path, with title as the running head (book.css sets the
    page size, margins and numbers); None, or why it failed."""
    with open(html_path, encoding='utf-8') as f:
        text = f.read()
    head = json.dumps(title, ensure_ascii=False)
    style = (f'<style>@page {{ @top-center {{ content: {head}; font: 9pt "Noto Sans", sans-serif; color: #666; }} }} '
             '@page :first { @top-center { content: none; } }</style>')
    printable = pdf_path + '.html'
    with open(printable, 'w', encoding='utf-8') as f:
        f.write(text.replace('</head>', style + '</head>', 1) if '</head>' in text else style + text)
    try:
        run = subprocess.run([chrome, '--headless', '--disable-gpu', '--no-sandbox', '--no-pdf-header-footer', '--virtual-time-budget=10000',
                              f'--print-to-pdf={pdf_path}', 'file://' + os.path.abspath(printable).replace(os.sep, '/')],
                             capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f'Chrome didn\'t print: {e}'
    finally:
        os.remove(printable)
    if not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) == 0:
        return f'Chrome printed nothing: {(run.stderr or run.stdout).strip()[-500:]}'
    return None


XHTML, OPS, NCX = 'http://www.w3.org/1999/xhtml', 'http://www.idpf.org/2007/ops', 'http://www.daisy.org/z3986/2005/ncx/'


def _pages_only(text, kind):
    """A navigation file (kind 'nav', the EPUB 3 nav.xhtml, or 'ncx', the EPUB 2 toc.ncx) with only its
    entries for whole pages: an entry pointing inside a page (#) goes, with what's under it."""
    ns = XHTML if kind == 'nav' else NCX
    for prefix, uri in (('', ns), ('epub', OPS)):
        ElementTree.register_namespace(prefix, uri)
    root = ElementTree.fromstring(text)
    entry, link, attr = (f'{{{ns}}}li', f'{{{ns}}}a', 'href') if kind == 'nav' else (f'{{{ns}}}navPoint', f'{{{ns}}}content', 'src')
    for parent in list(root.iter()):
        for child in list(parent):
            target = child.find(link)
            if child.tag == entry and target is not None and '#' in target.get(attr, ''):
                parent.remove(child)
    if kind == 'nav':
        for parent in list(root.iter()):
            for child in list(parent):
                if child.tag == f'{{{ns}}}ol' and not len(child):
                    parent.remove(child)
    else:
        for parent in list(root.iter(entry)):  # a page's top section listed under the page itself: fold it in
            src = parent.find(link).get(attr)
            for i, child in reversed(list(enumerate(parent))):
                if child.tag == entry and child.find(link).get(attr) == src:
                    parent.remove(child)
                    for j, grandchild in enumerate(child.findall(entry)):
                        parent.insert(i + j, grandchild)
        orders = {}
        for point in root.iter(entry):  # in reading order; a page listed twice keeps one number, as the NCX rules ask
            point.set('playOrder', str(orders.setdefault(point.find(link).get(attr), len(orders) + 1)))
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ElementTree.tostring(root, encoding='unicode')


def finish_epub(src, dst):
    """Copy the EPUB src to dst, finished: each page that holds inline SVG declared so in its package file
    (properties="svg"), which EPUB 3 requires and Sphinx's builder leaves out; and the reader's contents
    (nav.xhtml, toc.ncx) listing only whole pages, the cover, parts, sections, chapters and appendices,
    not the sections inside a chapter."""
    with zipfile.ZipFile(src) as zin:
        names = zin.namelist()
        opf = next(n for n in names if n.endswith('.opf'))
        base = posixpath.dirname(opf)
        svg = {n for n in names if n.endswith(('.xhtml', '.html')) and b'<svg' in zin.read(n)}

        def item(m):
            tag = m.group(0)
            href = re.search(r'href="([^"]+)"', tag)
            if href and posixpath.normpath(posixpath.join(base, href.group(1))) in svg and 'properties=' not in tag:
                tag = tag.replace('<item ', '<item properties="svg" ', 1)
            return tag
        changed = {opf: re.sub(r'<item\b[^>]*>', item, zin.read(opf).decode('utf-8'))}
        for n in names:
            kind = 'nav' if posixpath.basename(n) == 'nav.xhtml' else 'ncx' if n.endswith('.ncx') else None
            if kind:
                changed[n] = _pages_only(zin.read(n).decode('utf-8'), kind)
        with zipfile.ZipFile(dst, 'w') as zout:  # mimetype first and stored, as EPUB requires
            zout.writestr(zipfile.ZipInfo('mimetype'), zin.read('mimetype'), compress_type=zipfile.ZIP_STORED)
            for n in names:
                if n != 'mimetype':
                    zout.writestr(n, changed.get(n, zin.read(n)), compress_type=zipfile.ZIP_DEFLATED)
