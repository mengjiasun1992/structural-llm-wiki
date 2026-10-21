"""Small PDFs for the tests, written here so none is checked in.

  make(pages, outline=(), ...) -> bytes

pages are content streams (bytes); text(...) writes one. outline is
[(depth, title, page index, top or None)]. Options cover what lib/pdf.py
reads: compression, object streams with a cross-reference stream, fonts,
named destinations, a form XObject, an Info title, encryption.
"""

import zlib

HELVETICA = b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>'


def text(*lines, font=b'F1', size=12):
    """A content stream showing each (x, y, string) line, its string bytes as written."""
    out = []
    for x, y, s in lines:
        out.append(b'BT /%s %d Tf %g %g Td (%s) Tj ET' % (font, size, x, y, s))
    return b'\n'.join(out)


def lzw(data, early=1):
    """data LZW-compressed as a PDF's LZWDecode reads it (no table resets: keep inputs under 3,800 bytes)."""
    table, n, width, codes, w = {bytes([i]): i for i in range(256)}, 0, 9, [(256, 9)], b''
    for byte in data:
        if w + bytes([byte]) in table:
            w += bytes([byte])
            continue
        codes.append((table[w], width))
        table[w + bytes([byte])] = 258 + len(table) - 256
        n, w = n + 1, bytes([byte])
        if 258 + n - 1 + early >= (1 << width) and width < 12:
            width += 1
    if w:
        codes.append((table[w], width))
        n += 1
        if 258 + n - 1 + early >= (1 << width) and width < 12:
            width += 1
    codes.append((257, width))
    bits = ''.join(format(c, f'0{size}b') for c, size in codes)
    bits += '0' * (-len(bits) % 8)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


class _Writer:
    def __init__(self):
        self.objects = {}

    def add(self, body=None):
        num = len(self.objects) + 1
        self.objects[num] = body
        return num

    def stream(self, data, extra=b'', compress=True, filters=None):
        if filters is not None:
            info, raw = extra + b' /Filter ' + filters[0], filters[1]
        elif compress:
            info, raw = extra + b' /Filter /FlateDecode', zlib.compress(data)
        else:
            info, raw = extra, data
        return self.add(('stream', info, raw))


def make(pages, outline=(), *, title=None, compress=True, packed=False, fonts=None, names=None, xobject=None,
         encrypt=False, stream_filters=None):
    """A PDF of the given content streams.

    fonts: {name: callable(writer) -> font dictionary bytes}, every page's
    fonts (default /F1 Helvetica). names: 'dests' (the catalog's Dests),
    'tree' (a Names tree) or 'action' (GoTo actions) for the outline's
    destinations, instead of direct ones. xobject: a form's content stream,
    /X1 on every page. stream_filters: (filter name, raw bytes) for the
    first page's content, instead of compressing it.
    """
    w = _Writer()
    catalog, tree = w.add(), w.add()
    font_refs = {name: w.add(make_font(w)) for name, make_font in (fonts or {'F1': lambda w: HELVETICA}).items()}
    font_dict = b' '.join(b'/%s %d 0 R' % (name.encode(), num) for name, num in font_refs.items())
    xobj = b''
    if xobject is not None:
        form = w.stream(xobject, b'/Type /XObject /Subtype /Form /BBox [0 0 612 792] /Matrix [1 0 0 1 0 100] '
                                 b'/Resources << /Font << ' + font_dict + b' >> >>', compress)
        xobj = b' /XObject << /X1 %d 0 R >>' % form
    page_refs = []
    for i, content in enumerate(pages):
        c = w.stream(content, compress=compress, filters=stream_filters if i == 0 else None)
        page_refs.append(w.add(b'<< /Type /Page /Parent %d 0 R /MediaBox [0 0 612 792] /Contents %d 0 R >>' % (tree, c)))
    w.objects[tree] = (b'<< /Type /Pages /Kids [%s] /Count %d /Resources << /Font << %s >>%s >> >>'
                       % (b' '.join(b'%d 0 R' % p for p in page_refs), len(page_refs), font_dict, xobj))
    extra = b''
    if outline:
        extra += _outline(w, outline, page_refs, names)
    w.objects[catalog] = b'<< /Type /Catalog /Pages %d 0 R%s >>' % (tree, extra)
    info = w.add(b'<< /Title (%s) >>' % title) if title else None
    return _serialize(w, catalog, info, packed, compress, encrypt)


def _dest(page_ref, top):
    return b'[%d 0 R /XYZ 0 %g 0]' % (page_ref, top) if top is not None else b'[%d 0 R /Fit]' % page_ref


def _outline(w, outline, page_refs, names):
    root = w.add()
    nums = [w.add() for _ in outline]
    parents, children = {}, {}
    for i, (depth, *_rest) in enumerate(outline):
        parent = next((j for j in range(i - 1, -1, -1) if outline[j][0] < depth), None)
        parents[i] = parent
        children.setdefault(parent, []).append(i)
    named = []
    for i, (_depth, title, page, top) in enumerate(outline):
        dest = _dest(page_refs[page], top)
        if names in ('dests', 'tree'):
            key = b'sec%d' % i
            named.append((key, dest))
            target = b'/Dest (%s)' % key if names == 'tree' else b'/Dest /%s' % key
        elif names == 'action':
            target = b'/A << /S /GoTo /D %s >>' % dest
        else:
            target = b'/Dest %s' % dest
        siblings = children[parents[i]]
        k = siblings.index(i)
        links = b''
        if k + 1 < len(siblings):
            links += b' /Next %d 0 R' % nums[siblings[k + 1]]
        if i in children:
            links += b' /First %d 0 R /Last %d 0 R' % (nums[children[i][0]], nums[children[i][-1]])
        parent = root if parents[i] is None else nums[parents[i]]
        w.objects[nums[i]] = b'<< /Title (%s) /Parent %d 0 R %s%s >>' % (title, parent, target, links)
    top = children[None]
    w.objects[root] = b'<< /Type /Outlines /First %d 0 R /Last %d 0 R /Count %d >>' % (nums[top[0]], nums[top[-1]], len(outline))
    extra = b' /Outlines %d 0 R' % root
    if names == 'dests':
        extra += b' /Dests << %s >>' % b' '.join(b'/%s %s' % (k, d) for k, d in named)
    elif names == 'tree':
        half = len(named) // 2
        kids = [w.add(b'<< /Names [%s] >>' % b' '.join(b'(%s) %s' % (k, d) for k, d in part)) for part in (named[:half], named[half:])]
        extra += b' /Names << /Dests << /Kids [%d 0 R %d 0 R] >> >>' % tuple(kids)
    return extra


def _serialize(w, catalog, info, packed, compress, encrypt):
    out = bytearray(b'%PDF-1.5\n%\xe2\xe3\xcf\xd3\n')
    plain = {n: b for n, b in w.objects.items() if not isinstance(b, tuple)}
    if packed:  # every plain object into one object stream
        head, body = [], bytearray()
        for n, b in plain.items():
            head.append(b'%d %d' % (n, len(body)))
            body += b + b'\n'
        first = b' '.join(head) + b'\n'
        num = len(w.objects) + 1
        data = first + bytes(body)
        w.objects[num] = ('stream', b'/Type /ObjStm /N %d /First %d' % (len(plain), len(first)), data)
        if compress:
            w.objects[num] = ('stream', w.objects[num][1] + b' /Filter /FlateDecode', zlib.compress(data))
    for n, b in w.objects.items():
        if packed and n in plain:
            continue
        out += b'%d 0 obj\n' % n
        if isinstance(b, tuple):
            out += b'<< %s /Length %d >>\nstream\n' % (b[1], len(b[2])) + b[2] + b'\nendstream'
        else:
            out += b
        out += b'\nendobj\n'
    tail = b'/Root %d 0 R%s%s' % (catalog, b' /Info %d 0 R' % info if info else b'',
                                  b' /Encrypt << /Filter /Standard /V 1 >>' if encrypt else b'')
    if packed:
        xref = len(w.objects) + 1
        out += b'%d 0 obj\n<< /Type /XRef /Size %d %s /Length 0 >>\nstream\n\nendstream\nendobj\n' % (xref, xref + 1, tail)
    else:
        out += b'xref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size %d %s >>\n' % (len(w.objects) + 1, tail)
    out += b'startxref\n0\n%%EOF\n'
    return bytes(out)
