"""A PDF's text layer as markdown (design doc §4.3), with the standard library only.

  read(data) -> Document: its pages as lines of text, its outline and its title
  markdown(doc) -> the text, each outline title a heading where it points
      (## Page <n> headings for a PDF without an outline)
  slices(doc, text) -> [(title, page, markdown)]: an outlined PDF over
      SLICE_PAGES pages, one slice per top-level outline entry; [] otherwise

PdfError says what can't be read (encrypted, no text layer, a filter this
doesn't know, a broken file), so the caller records a link instead.
"""

import base64
import re
import statistics
import unicodedata
import zlib

SLICE_PAGES = 100
MAX_DEPTH = 12  # page trees, outlines and forms nested deeper are left out
PLACEHOLDER_TITLE = re.compile(r'(untitled|microsoft word - .*|.*\.(docx?|pdf|tex|dvi|indd))\Z', re.I)  # a producer's, not the document's


class PdfError(Exception):
    pass


class Name(str):
    """A PDF name (/Like this)."""


class Op(str):
    """A keyword or content-stream operator."""


class Mark(str):
    """A delimiter: [ ] << >>, or '' at the end."""


class Ref(tuple):
    """An indirect reference: (number, generation)."""


class Stream:
    def __init__(self, info, raw):
        self.info, self.raw = info, raw


_REGULAR = re.compile(rb'[^\s()<>\[\]{}/%\x00]+')
_NAME = re.compile(rb'/([^\s()<>\[\]{}/%\x00]*)')
_NUMBER = re.compile(rb'[+-]?(\d+\.?\d*|\.\d+)\Z')
_OCTAL = re.compile(rb'[0-7]{1,3}')
_ESCAPES = {b'n': b'\n', b'r': b'\r', b't': b'\t', b'b': b'\b', b'f': b'\f'}
_WHITE = b' \t\r\n\x00\x0c'


class Lexer:
    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def token(self):
        """The next token: a number, bytes (a string), Name, Op, bool, None, or a Mark."""
        d, n = self.data, len(self.data)
        while self.pos < n:
            c = d[self.pos]
            if c in _WHITE:
                self.pos += 1
            elif c == 37:  # % comment
                while self.pos < n and d[self.pos] not in b'\r\n':
                    self.pos += 1
            elif c == 40:  # (
                return self._literal()
            elif c == 60:  # <
                if d[self.pos + 1:self.pos + 2] == b'<':
                    self.pos += 2
                    return Mark('<<')
                end = d.find(b'>', self.pos)
                if end < 0:
                    raise PdfError('a broken hex string')
                digits = re.sub(rb'[^0-9A-Fa-f]', b'', d[self.pos + 1:end])
                self.pos = end + 1
                return bytes.fromhex((digits + b'0' * (len(digits) % 2)).decode())
            elif c == 62 and d[self.pos + 1:self.pos + 2] == b'>':
                self.pos += 2
                return Mark('>>')
            elif c in b'[]':
                self.pos += 1
                return Mark(chr(c))
            elif c == 47:  # /
                m = _NAME.match(d, self.pos)
                self.pos = m.end()
                return Name(re.sub(rb'#([0-9A-Fa-f]{2})', lambda x: bytes([int(x.group(1), 16)]), m.group(1)).decode('latin-1'))
            else:
                m = _REGULAR.match(d, self.pos)
                if not m:  # a stray ) > { or }
                    self.pos += 1
                    continue
                self.pos = m.end()
                word = m.group()
                if _NUMBER.match(word):
                    return float(word) if b'.' in word else int(word)
                return {b'true': True, b'false': False, b'null': None}.get(word, Op(word.decode('latin-1')))
        return Mark('')

    def _literal(self):
        d, i, depth, out = self.data, self.pos + 1, 1, bytearray()
        while i < len(d):
            c = d[i]
            if c == 92:  # backslash
                e = d[i + 1:i + 2]
                m = _OCTAL.match(d, i + 1)
                if e in _ESCAPES:
                    out += _ESCAPES[e]
                    i += 2
                elif m:
                    out.append(int(m.group(), 8) & 255)
                    i = m.end()
                elif e in (b'\r', b'\n'):  # a line continuation
                    i += 3 if d[i + 1:i + 3] == b'\r\n' else 2
                else:
                    out += e
                    i += 2
                continue
            depth += {40: 1, 41: -1}.get(c, 0)
            if not depth:
                self.pos = i + 1
                return bytes(out)
            out.append(c)
            i += 1
        raise PdfError('a broken string')

    def value(self, tok=None):
        """The next object, its arrays and dictionaries built and references joined."""
        tok = self.token() if tok is None else tok
        if isinstance(tok, Mark) and tok in ('[', '<<'):
            close, items = (']' if tok == '[' else '>>'), []
            while True:
                t = self.token()
                if isinstance(t, Mark) and t in (close, ''):
                    break
                items.append(self.value(t) if isinstance(t, Mark) else t)
            items = _refs(items)
            if tok == '[':
                return items
            return {str(items[i]): items[i + 1] for i in range(0, len(items) - 1, 2) if isinstance(items[i], Name)}
        return tok


def _refs(items):
    out = []
    for it in items:
        if isinstance(it, Op) and it == 'R' and len(out) >= 2 and type(out[-1]) is int and type(out[-2]) is int:
            gen, num = out.pop(), out.pop()
            out.append(Ref((num, gen)))
        else:
            out.append(it)
    return out


def _object_at(data, pos):
    lx = Lexer(data, pos)
    obj = lx.value()
    if not isinstance(obj, dict) or lx.token() != 'stream':
        return obj
    start = lx.pos + (2 if data[lx.pos:lx.pos + 2] == b'\r\n' else 1)
    length = obj.get('Length')
    if type(length) is int and data[start + length:start + length + 32].lstrip().startswith(b'endstream'):
        return Stream(obj, data[start:start + length])
    end = data.find(b'endstream', start)
    if end < 0:
        raise PdfError('a broken stream')
    return Stream(obj, data[start:end].rstrip(b'\r\n'))


def text_string(s):
    """A PDF text string (a title) as str."""
    if not isinstance(s, bytes):
        return ''
    if s[:2] == b'\xfe\xff':
        return s[2:].decode('utf-16-be', 'replace')
    return s.decode('latin-1')


class Document:
    def __init__(self, data):
        if b'%PDF-' not in data[:1024]:
            raise PdfError('not a PDF')
        if re.search(rb'/Encrypt\s*(\d+\s+\d+\s+R|<<)', data):
            raise PdfError('the PDF is encrypted')
        self.data, self.cache, self.packed, self.offsets, self.named = data, {}, {}, {}, None
        for m in re.finditer(rb'(?<![\d.])(\d+)\s+(\d+)\s+obj\b', data):
            self.offsets[int(m.group(1))] = m.end()  # a later revision wins
        for num, off in list(self.offsets.items()):
            if self._typed(off, b'ObjStm'):
                self._unpack(self.get(Ref((num, 0))))
        root = self._root()
        self.pages, page_of = [], {}
        self._walk(root.get('Pages'), None, page_of, 0)
        if not self.pages:
            raise PdfError('the PDF has no pages')
        infos = [self.get(t.get('Info')) for t in self._trailers()]
        titles = [' '.join(text_string(self.get(i.get('Title'))).split()) for i in infos if isinstance(i, dict)]
        self.title = next((x for x in titles if x and not PLACEHOLDER_TITLE.match(x)), '')
        self.outline = []
        outlines = self.get(root.get('Outlines'))
        if isinstance(outlines, dict):
            self._outline(outlines.get('First'), 0, page_of, root, set())

    def _typed(self, off, kind):
        """Whether the object at off is a stream dictionary of /Type kind, judged by its own dictionary only."""
        head = self.data[off:off + 400].split(b'endobj')[0].split(b'stream')[0]
        return re.search(rb'/Type\s*/' + kind + rb'\b', head) is not None

    def get(self, x, default=None):
        """x with references followed; default when that leads nowhere."""
        seen = 0
        while isinstance(x, Ref) and seen < 32:
            num, seen = x[0], seen + 1
            if num not in self.cache:
                self.cache[num] = None  # a reference to itself leads nowhere
                try:
                    if num in self.offsets:
                        self.cache[num] = _object_at(self.data, self.offsets[num])
                    elif num in self.packed:
                        body, pos = self.packed[num]
                        self.cache[num] = Lexer(body, pos).value()
                except (PdfError, IndexError, ValueError):
                    pass
            x = self.cache[num]
        return default if x is None or isinstance(x, Ref) else x

    def decode(self, stream):
        data = stream.raw
        filters = self.get(stream.info.get('Filter'), [])
        for f in filters if isinstance(filters, list) else [filters]:
            f = self.get(f)
            try:
                if f in ('FlateDecode', 'Fl'):
                    data = zlib.decompressobj().decompress(data)
                elif f in ('ASCIIHexDecode', 'AHx'):
                    digits = re.sub(rb'[^0-9A-Fa-f]', b'', data.split(b'>')[0])
                    data = bytes.fromhex((digits + b'0' * (len(digits) % 2)).decode())
                elif f in ('ASCII85Decode', 'A85'):
                    data = base64.a85decode(re.sub(rb'\s', b'', data).split(b'~>')[0].lstrip(b'<~'))
                else:
                    raise PdfError(f'a stream compressed with {f}, which this can\'t read')
            except (zlib.error, ValueError) as e:
                raise PdfError(f'a broken stream: {e}') from None
        return data

    def _unpack(self, stream):
        if not isinstance(stream, Stream):
            return
        body = self.decode(stream)
        head, first = Lexer(body), self.get(stream.info.get('First'), 0)
        for _ in range(self.get(stream.info.get('N'), 0)):
            num, off = head.token(), head.token()
            if type(num) is int and type(off) is int and num not in self.offsets:
                self.packed[num] = (body, first + off)

    def _trailers(self):
        """The trailer dictionaries, newest first: classic ones, then cross-reference streams."""
        found = [Lexer(self.data, m.end()).value() for m in reversed(list(re.finditer(rb'trailer\s*(?=<<)', self.data)))]
        found += [self.get(Ref((n, 0))).info for n, off in sorted(self.offsets.items(), key=lambda x: -x[1])
                  if self._typed(off, b'XRef') and isinstance(self.get(Ref((n, 0))), Stream)]
        return [t for t in found if isinstance(t, dict)]

    def _root(self):
        for trailer in self._trailers():
            root = self.get(trailer.get('Root'))
            if isinstance(root, dict):
                return root
        for num in sorted(set(self.offsets) | set(self.packed)):
            obj = self.get(Ref((num, 0)))
            if isinstance(obj, dict) and obj.get('Type') == 'Catalog':
                return obj
        raise PdfError('a broken PDF: no catalog')

    def _walk(self, ref, resources, page_of, depth):
        node = self.get(ref)
        if not isinstance(node, dict) or depth > MAX_DEPTH:
            return
        resources = node.get('Resources', resources)
        kids = self.get(node.get('Kids'))
        if node.get('Type') != 'Page' and isinstance(kids, list):
            for kid in kids:
                self._walk(kid, resources, page_of, depth + 1)
            return
        if isinstance(ref, Ref):
            page_of[ref[0]] = len(self.pages)
        self.pages.append(_lines(self, node, self.get(resources, {})))

    def _destination(self, node, page_of, root):
        """(page index, top or None) an outline item points to, or None."""
        dest = node.get('Dest')
        action = self.get(node.get('A'))
        if dest is None and isinstance(action, dict) and action.get('S') == 'GoTo':
            dest = action.get('D')
        dest = self.get(dest)
        if isinstance(dest, (bytes, Name)):
            dest = self.get(self._names(root).get(dest.decode('latin-1') if isinstance(dest, bytes) else str(dest)))
        if isinstance(dest, dict):
            dest = self.get(dest.get('D'))
        if not isinstance(dest, list) or not dest:
            return None
        page = page_of.get(dest[0][0]) if isinstance(dest[0], Ref) else dest[0] if type(dest[0]) is int else None
        top = dest[3] if len(dest) > 3 and dest[1] == 'XYZ' else dest[2] if len(dest) > 2 and dest[1] in ('FitH', 'FitBH') else None
        return None if page is None or not 0 <= page < len(self.pages) else (page, top if isinstance(top, (int, float)) else None)

    def _names(self, root):
        """The named destinations: the catalog's Dests and its Names tree."""
        if self.named is None:
            dests = self.get(root.get('Dests'))
            self.named = dict(dests) if isinstance(dests, dict) else {}

            def walk(node, depth):
                node = self.get(node)
                if not isinstance(node, dict) or depth > MAX_DEPTH:
                    return
                pairs = self.get(node.get('Names'), [])
                for i in range(0, len(pairs) - 1, 2):
                    if isinstance(pairs[i], bytes):
                        self.named[pairs[i].decode('latin-1')] = pairs[i + 1]
                for kid in self.get(node.get('Kids'), []):
                    walk(kid, depth + 1)
            names = self.get(root.get('Names'))
            walk(names.get('Dests') if isinstance(names, dict) else None, 0)
        return self.named

    def _outline(self, item, depth, page_of, root, seen):
        while item is not None and depth <= MAX_DEPTH:
            if isinstance(item, Ref):
                if item in seen:
                    return
                seen.add(item)
            node = self.get(item)
            if not isinstance(node, dict):
                return
            title = ' '.join(text_string(self.get(node.get('Title'))).split())
            where = self._destination(node, page_of, root)
            if title and where:
                self.outline.append((depth, title, where[0], where[1]))
            self._outline(node.get('First'), depth + 1, page_of, root, seen)
            item = node.get('Next')


# Text: fonts, then the content stream.

_GLYPHS = {
    'space': ' ', 'exclam': '!', 'quotedbl': '"', 'numbersign': '#', 'dollar': '$', 'percent': '%', 'ampersand': '&',
    'quotesingle': "'", 'quoteright': '’', 'quoteleft': '‘', 'parenleft': '(', 'parenright': ')', 'asterisk': '*',
    'plus': '+', 'comma': ',', 'hyphen': '-', 'period': '.', 'slash': '/', 'colon': ':', 'semicolon': ';', 'less': '<',
    'equal': '=', 'greater': '>', 'question': '?', 'at': '@', 'bracketleft': '[', 'backslash': '\\', 'bracketright': ']',
    'asciicircum': '^', 'underscore': '_', 'grave': '`', 'braceleft': '{', 'bar': '|', 'braceright': '}', 'asciitilde': '~',
    'endash': '–', 'emdash': '—', 'quotedblleft': '“', 'quotedblright': '”', 'bullet': '•',
    'dagger': '†', 'daggerdbl': '‡', 'section': '§', 'paragraph': '¶', 'ellipsis': '…',
    'minus': '−', 'multiply': '×', 'divide': '÷', 'degree': '°', 'plusminus': '±',
    'copyright': '©', 'registered': '®', 'trademark': '™', 'dotlessi': 'ı', 'germandbls': 'ß',
    'ae': 'æ', 'AE': 'Æ', 'oe': 'œ', 'OE': 'Œ', 'oslash': 'ø', 'Oslash': 'Ø',
    'fi': 'fi', 'fl': 'fl', 'ff': 'ff', 'ffi': 'ffi', 'ffl': 'ffl', 'periodcentered': '·',
    'infinity': '∞', 'lessequal': '≤', 'greaterequal': '≥', 'notequal': '≠', 'arrowright': '→',
}
_DIGITS = 'zero one two three four five six seven eight nine'.split()
_ACCENTS = {'acute': 'ACUTE', 'grave': 'GRAVE', 'circumflex': 'CIRCUMFLEX', 'dieresis': 'DIAERESIS', 'tilde': 'TILDE',
            'cedilla': 'CEDILLA', 'ring': 'RING ABOVE', 'caron': 'CARON'}


def glyph(name):
    """The text of a glyph name (the Adobe glyph list's common names, uniXXXX and uXXXX); '' when unknown."""
    if name in _GLYPHS:
        return _GLYPHS[name]
    if len(name) == 1 and name.isalpha():
        return name
    if name in _DIGITS:
        return str(_DIGITS.index(name))
    m = re.fullmatch(r'uni((?:[0-9A-Fa-f]{4})+)', name) or re.fullmatch(r'u([0-9A-Fa-f]{4,6})', name)
    if m:
        hexs = m.group(1)
        step = 4 if name.startswith('uni') else len(hexs)
        return ''.join(chr(int(hexs[i:i + step], 16)) for i in range(0, len(hexs), step))
    if '.' in name:  # a variant, such as a.sc
        return glyph(name.split('.')[0])
    letter = 'CAPITAL' if name[:1].isupper() else 'SMALL'
    for full in ([f'LATIN {letter} LETTER {name[0].upper()} WITH {_ACCENTS[name[1:]]}'] if name[1:] in _ACCENTS else []) + [f'GREEK {letter} LETTER {name.upper()}']:
        try:
            return unicodedata.lookup(full)
        except KeyError:
            pass
    return ''


def _utf16(hexs, add=0):
    raw = bytes.fromhex(hexs.decode())
    if add:
        raw = (int.from_bytes(raw, 'big') + add).to_bytes(len(raw), 'big')
    return raw.decode('utf-16-be', 'replace')


class Font:
    def __init__(self, doc, font):
        font = doc.get(font, {})
        font = font if isinstance(font, dict) else {}
        self.two = font.get('Subtype') == 'Type0'  # two-byte codes
        self.map, self.diffs, self.widths = {}, {}, {}
        cmap = doc.get(font.get('ToUnicode'))
        if isinstance(cmap, Stream):
            try:
                self._cmap(doc.decode(cmap))
            except PdfError:
                pass
        enc = doc.get(font.get('Encoding'))
        base = doc.get(enc.get('BaseEncoding')) if isinstance(enc, dict) else enc
        self.codec = {'WinAnsiEncoding': 'cp1252', 'MacRomanEncoding': 'mac_roman'}.get(base, 'latin-1')
        code = 0
        for item in doc.get(enc.get('Differences'), []) if isinstance(enc, dict) else []:
            if type(item) is int:
                code = item
            elif isinstance(item, Name):
                self.diffs[code], code = glyph(item), code + 1
        if self.two:
            desc = doc.get((doc.get(font.get('DescendantFonts'), [None]) or [None])[0], {})
            self.default = doc.get(desc.get('DW'), 1000) if isinstance(desc, dict) else 1000
            w = [doc.get(x) for x in doc.get(desc.get('W'), [])] if isinstance(desc, dict) else []
            i = 0
            while i + 1 < len(w):
                if isinstance(w[i + 1], list):
                    self.widths.update({w[i] + j: x for j, x in enumerate(w[i + 1])})
                    i += 2
                elif i + 2 < len(w):
                    self.widths.update({c: w[i + 2] for c in range(w[i], min(w[i + 1], w[i] + 65535) + 1)})
                    i += 3
                else:
                    break
        else:
            self.default = 500  # a standard font without widths: about half an em
            first = doc.get(font.get('FirstChar'), 0)
            self.widths = {first + j: doc.get(x) for j, x in enumerate(doc.get(font.get('Widths'), []))}

    def _cmap(self, text):
        for block in re.findall(rb'beginbfchar(.*?)endbfchar', text, re.S):
            for src, dst in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>', block):
                self.map[int(src, 16)] = _utf16(dst)
        for block in re.findall(rb'beginbfrange(.*?)endbfrange', text, re.S):
            for lo, hi, dst in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<[0-9A-Fa-f]*>|\[[^\]]*\])', block):
                lo, hi = int(lo, 16), min(int(hi, 16), int(lo, 16) + 65535)
                if dst.startswith(b'['):
                    for i, d in enumerate(re.findall(rb'<([0-9A-Fa-f]*)>', dst)):
                        self.map[lo + i] = _utf16(d)
                else:
                    for code in range(lo, hi + 1):
                        self.map[code] = _utf16(dst[1:-1], code - lo)

    def codes(self, s):
        return [s[i] << 8 | s[i + 1] for i in range(0, len(s) - 1, 2)] if self.two else list(s)

    def text(self, code):
        if code in self.map:
            return self.map[code]
        if self.two:
            return ''  # a glyph number with no text behind it
        if code in self.diffs:
            return self.diffs[code]
        return bytes([code]).decode(self.codec, 'replace')

    def width(self, code):
        w = self.widths.get(code, self.default)
        return (w if isinstance(w, (int, float)) else self.default) / 1000


IDENTITY = (1, 0, 0, 1, 0, 0)


def _mul(m, n):
    """m then n."""
    a, b, c, d, e, f = m
    p, q, r, s, t, u = n
    return (a * p + b * r, a * q + b * s, c * p + d * r, c * q + d * s, e * p + f * r + t, e * q + f * s + u)


def _lines(doc, page, resources):
    """A page's text as [(y, size, line)], top to bottom as the page draws it."""
    contents = doc.get(page.get('Contents'))
    streams = [doc.get(s) for s in (contents if isinstance(contents, list) else [contents])]
    data = b'\n'.join(doc.decode(s) for s in streams if isinstance(s, Stream))
    runs = []
    _run(doc, data, resources, IDENTITY, runs, {}, 0)
    return _join(runs)


def _run(doc, data, resources, ctm, runs, fonts, depth):
    st = {'ctm': ctm, 'tm': IDENTITY, 'lm': IDENTITY, 'font': None, 'size': 0, 'tc': 0, 'tw': 0, 'th': 1, 'tl': 0}
    stack, operands, lx = [], [], Lexer(data)
    font_res = doc.get(resources.get('Font'), {}) if isinstance(resources, dict) else {}
    xobjects = doc.get(resources.get('XObject'), {}) if isinstance(resources, dict) else {}

    def show(s):
        font = st['font']
        if not isinstance(s, bytes) or font is None:
            return
        text, adv = [], 0
        for code in font.codes(s):
            text.append(font.text(code))
            adv += (font.width(code) * st['size'] + st['tc'] + (st['tw'] if code == 32 and not font.two else 0)) * st['th']
        m = _mul(st['tm'], st['ctm'])
        end = _mul((1, 0, 0, 1, adv, 0), m)
        runs.append((m[5], m[4], end[4], abs(st['size']) * (abs(m[3]) or abs(m[2]) or 1), ''.join(text)))
        st['tm'] = _mul((1, 0, 0, 1, adv, 0), st['tm'])

    def move(tx, ty):
        st['lm'] = st['tm'] = _mul((1, 0, 0, 1, tx, ty), st['lm'])

    while True:
        tok = lx.token()
        if isinstance(tok, Mark) and tok == '':
            return
        if not isinstance(tok, Op):
            operands.append(lx.value(tok) if isinstance(tok, Mark) else tok)
            continue
        op, args, operands = str(tok), operands, []
        try:
            if op == 'q':
                stack.append(dict(st))
            elif op == 'Q' and stack:
                st.update(stack.pop())
            elif op == 'cm':
                st['ctm'] = _mul(tuple(args[-6:]), st['ctm'])
            elif op == 'BT':
                st['tm'] = st['lm'] = IDENTITY
            elif op == 'Tf':
                name = str(args[-2])
                if name not in fonts:
                    fonts[name] = Font(doc, font_res.get(name)) if isinstance(font_res, dict) else Font(doc, None)
                st['font'], st['size'] = fonts[name], args[-1]
            elif op in ('Tc', 'Tw', 'TL'):
                st[op.lower()] = args[-1]
            elif op == 'Tz':
                st['th'] = args[-1] / 100
            elif op in ('Td', 'TD'):
                move(args[-2], args[-1])
                st['tl'] = -args[-1] if op == 'TD' else st['tl']
            elif op == 'Tm':
                st['lm'] = st['tm'] = tuple(args[-6:])
            elif op == 'T*':
                move(0, -st['tl'])
            elif op == 'Tj':
                show(args[-1])
            elif op in ("'", '"'):
                if op == '"':
                    st['tw'], st['tc'] = args[-3], args[-2]
                move(0, -st['tl'])
                show(args[-1])
            elif op == 'TJ':
                for item in args[-1]:
                    if isinstance(item, (int, float)):
                        st['tm'] = _mul((1, 0, 0, 1, -item / 1000 * st['size'] * st['th'], 0), st['tm'])
                    else:
                        show(item)
            elif op == 'Do' and depth < MAX_DEPTH:
                form = doc.get(xobjects.get(str(args[-1]))) if isinstance(xobjects, dict) else None
                if isinstance(form, Stream) and form.info.get('Subtype') == 'Form':
                    matrix = tuple(doc.get(form.info.get('Matrix'), IDENTITY))
                    _run(doc, doc.decode(form), doc.get(form.info.get('Resources'), resources), _mul(matrix, st['ctm']), runs, {}, depth + 1)
            elif op == 'ID':  # inline image data: skip to EI
                m = re.compile(rb'\sEI(?=[\s]|\Z)').search(data, lx.pos)
                lx.pos = m.end() if m else len(data)
        except (TypeError, ValueError, IndexError, ZeroDivisionError):
            pass  # an operator with operands it can't use: skip it


_LIGATURES = {'ﬀ': 'ff', 'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬃ': 'ffi', 'ﬄ': 'ffl', 'ﬅ': 'st', 'ﬆ': 'st', ' ': ' '}


def _clean(text):
    text = ''.join(_LIGATURES.get(c, c) for c in text if c >= ' ' or c == '\t')
    return ' '.join(text.split())


def _join(runs):
    """Runs of text into lines: the same baseline continues a line, with a space for a gap."""
    lines = []
    for y, x0, x1, size, text in runs:
        size = size or 1
        cur = lines[-1] if lines else None
        if cur and abs(y - cur[0]) <= 0.5 * max(size, cur[2]) and x0 >= cur[1] - 2 * size:
            if x0 - cur[1] > 0.15 * size and not cur[3][-1].endswith(' ') and not text.startswith(' '):
                cur[3].append(' ')
            cur[3].append(text)
            cur[1] = x1
        else:
            lines.append([y, x1, size, [text]])
    out = [(y, size, _clean(''.join(parts))) for y, _, size, parts in lines]
    return [line for line in out if line[2]]


# Markdown.

def _key(text):
    return re.sub(r'[\W_]+', '', text.lower())


def _numbered(line, key):
    """Whether a line is the title, maybe after its section number (1.2 Title)."""
    return bool(key) and line.endswith(key) and (line == key or line[:-len(key)].isdigit())


def _page_markdown(lines, entries):
    """A page's lines as paragraphs, with its outline entries placed as headings."""
    gaps = [a[0] - b[0] for a, b in zip(lines, lines[1:]) if a[0] - b[0] > 0]
    usual = statistics.median(gaps) if gaps else 0
    items = [('line', y, size, text) for y, size, text in lines]
    at = 0
    for depth, title, _, top in entries:
        heading = ('heading', '#' * min(depth + 2, 6) + ' ' + title)
        key = _key(title)
        match = next((i for i in range(at, len(items)) if items[i][0] == 'line' and _numbered(_key(items[i][3]), key)), None)
        if match is not None and key:
            items[match] = heading
            at = match + 1
            continue
        if top is not None:
            below = next((i for i in range(at, len(items)) if items[i][0] == 'line' and items[i][1] <= top + 0.5 * items[i][2]), len(items))
            at = below
        items.insert(at, heading)
        at += 1
    out, prev = [], None
    for item in items:
        if item[0] == 'heading':
            out += ['', item[1], '']
            prev = None
            continue
        _, y, size, text = item
        if prev is not None and (prev - y > 1.4 * usual > 0 or y > prev):
            out.append('')
        out.append('\\' + text if text.startswith(('#', '>')) else text)
        prev = y
    return '\n'.join(out).strip('\n')


def markdown(doc):
    by_page = {}
    for entry in doc.outline:
        by_page.setdefault(entry[2], []).append(entry)
    parts = [f'# {doc.title}'] if doc.title else []
    for i, lines in enumerate(doc.pages):
        if not doc.outline:
            parts.append(f'## Page {i + 1}')
        body = _page_markdown(lines, by_page.get(i, []))
        if body:
            parts.append(body)
    return re.sub(r'\n{3,}', '\n\n', '\n\n'.join(parts)).strip() + '\n'


def read(data):
    doc = Document(data)
    if not any(lines for lines in doc.pages):
        raise PdfError('the PDF has no text layer (a scan?)')
    return doc


def slices(doc, text):
    """[(title, page, markdown)], one per top-level outline entry, for an outlined PDF over SLICE_PAGES pages."""
    tops = [e for e in doc.outline if e[0] == 0]
    if len(doc.pages) <= SLICE_PAGES or len(tops) < 2:
        return []
    chunks = re.split(r'(?m)^(?=## )', text)
    front, chunks = (chunks[0], chunks[1:]) if not chunks[0].startswith('## ') else ('', chunks)
    page = {title: p for _, title, p, _ in reversed(tops)}
    out = []
    for i, chunk in enumerate(chunks):
        title = chunk.split('\n', 1)[0][3:].strip()
        body = (front.rstrip() + '\n\n' + chunk if i == 0 and front.strip() else chunk).strip() + '\n'
        out.append((title, page.get(title), body))
    return out
