"""Small EPUBs for the tests, written here so none is checked in.

  make(chapters, toc=(), title='Book', version=3, encrypted=(), ...) -> bytes

chapters are [(file name, XHTML body)]; toc is [(depth, title, href)]. EPUB 3
gets a navigation document, EPUB 2 an NCX. encrypted lists files
META-INF/encryption.xml marks, with algorithm.
"""

import io
import zipfile

ENC = 'http://www.w3.org/2001/04/xmlenc#aes128-cbc'
FONTS = 'http://www.idpf.org/2008/embedding'


def page(body, title='Chapter'):
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" '
            f'xmlns:epub="http://www.idpf.org/2007/ops"><head><title>{title}</title></head><body>{body}</body></html>')


def _nav(toc):
    def items(i, depth):
        out = []
        while i < len(toc) and toc[i][0] == depth:
            d, title, href = toc[i]
            i += 1
            sub = ''
            if i < len(toc) and toc[i][0] > depth:
                sub, i = items(i, depth + 1)
                sub = f'<ol>{sub}</ol>'
            out.append(f'<li><a href="{href}">{title}</a>{sub}</li>')
        return ''.join(out), i
    return page(f'<nav epub:type="toc"><h1>Contents</h1><ol>{items(0, 0)[0]}</ol></nav>', 'Contents')


def _ncx(toc):
    def points(i, depth):
        out = []
        while i < len(toc) and toc[i][0] == depth:
            d, title, href = toc[i]
            i += 1
            sub = ''
            if i < len(toc) and toc[i][0] > depth:
                sub, i = points(i, depth + 1)
            out.append(f'<navPoint id="p{i}"><navLabel><text>{title}</text></navLabel><content src="{href}"/>{sub}</navPoint>')
        return ''.join(out), i
    return ('<?xml version="1.0"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
            f'<navMap>{points(0, 0)[0]}</navMap></ncx>')


def make(chapters, toc=(), title='Book', version=3, encrypted=(), linear_no=(), folder='OEBPS'):
    toc, at = list(toc), f'{folder}/' if folder else ''
    items = [f'<item id="c{i}" href="{name}" media-type="application/xhtml+xml"/>' for i, (name, _) in enumerate(chapters)]
    refs = [f'<itemref idref="c{i}"' + (' linear="no"' if name in linear_no else '') + '/>' for i, (name, _) in enumerate(chapters)]
    files = {f'{at}{name}': page(body) for name, body in chapters}
    if toc and version == 3:
        items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
        files[f'{at}nav.xhtml'] = _nav(toc)
    elif toc:
        items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
        files[f'{at}toc.ncx'] = _ncx(toc)
    title_xml = f'<dc:title>{title}</dc:title>' if title else ''
    files[f'{at}content.opf'] = (
        f'<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="{version}.0">'
        f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">{title_xml}</metadata>'
        f'<manifest>{"".join(items)}</manifest><spine>{"".join(refs)}</spine></package>')
    files['META-INF/container.xml'] = (
        '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        f'<rootfiles><rootfile full-path="{at}content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    if encrypted:
        refs_xml = ''.join(f'<EncryptedData xmlns="http://www.w3.org/2001/04/xmlenc#"><EncryptionMethod Algorithm="{alg}"/>'
                           f'<CipherData><CipherReference URI="{at}{name}"/></CipherData></EncryptedData>' for name, alg in encrypted)
        files['META-INF/encryption.xml'] = f'<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container">{refs_xml}</encryption>'
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        for name, text in files.items():
            z.writestr(name, text, compress_type=zipfile.ZIP_DEFLATED)
    return out.getvalue()
