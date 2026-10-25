"""A fetched source as the markdown the wiki saves (design doc §4.3), the same
way for fetch-source and check-upstream.

  convert(kind, data, url, content_type='', include=None, name='')
      -> (markdown bytes, [(title, fragment, markdown)] slices of a long outlined PDF or EPUB)

A slice's fragment finds it again in its source's URL: page=N for a PDF,
chapter=N for an EPUB.

ConvertError says why a source can't be saved as a copy.
"""

import os

from . import epub, fetch, html2md, pdf, plaintext, tex

LINK = 'record it as a link (manifest.py put-source --kind link)'


class ConvertError(Exception):
    pass


def convert(kind, data, url, content_type='', include=None, name=''):
    if kind is None:
        raise ConvertError(f'not markdown, text, HTML, PDF or EPUB; {LINK}')
    if kind == 'pdf':
        try:
            doc = pdf.read(data)
        except pdf.PdfError as e:
            raise ConvertError(f'{e}; {LINK}') from None
        text = pdf.markdown(doc)
        return text.encode(), [(t, None if page is None else f'page={page + 1}', md) for t, page, md in pdf.slices(doc, text)]
    if kind == 'epub':
        try:
            book = epub.read(data)
        except epub.EpubError as e:
            raise ConvertError(f'{e}; {LINK}') from None
        text = epub.markdown(book)
        return text.encode(), epub.slices(book, text)
    if kind == 'tex':
        return tex.convert(data.decode('utf-8', 'replace'), include).encode(), []
    if kind == 'html':
        page = data.decode(fetch.charset(content_type) or 'utf-8', 'replace')
        return html2md.convert(page, url)[0].encode(), []
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        raise ConvertError('the text isn\'t UTF-8; save a UTF-8 copy and pass it with --file') from None
    if kind == 'code':
        return plaintext.code(text, name).encode(), []
    markdown = 'markdown' in content_type or os.path.splitext(name.split('?')[0])[1].lower() in ('.md', '.markdown')
    standard = None if markdown else plaintext.standard(text)
    return (standard.encode() if standard else data), []
