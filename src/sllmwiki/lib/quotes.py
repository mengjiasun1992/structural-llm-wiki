"""Quotations in a narrative (design doc §4.7): each must appear in the source
section it cites, word for word, and be at most max_quote_words long.

check(root, rel, text, max_words) -> findings:
  QUOTE_NOT_FOUND   a cited quotation its section doesn't contain
  QUOTE_TOO_LONG    a quotation over max_words

A quotation is text in double quotes ("..." or “...”) of three words or more;
shorter is a term or a name. It's checked against the first citation after it,
before the next quotation on its line; one without a citation is only checked
for length. Matching ignores case, markdown emphasis and links, escapes, quote
marks, kinds of dash, TeX for Greek letters, and a PDF's line-break hyphens; an
ellipsis splits a quotation into parts that must appear in order.
"""

import re
import unicodedata

from . import citations, language, search
from .compat import mask_code_spans, scan

QUOTE = re.compile(r'"([^"\n]+)"|“([^”\n]+)”|「([^」\n]+)」')
MIN_WORDS = 3  # shorter text in quotes is a term or a name, not a quotation
_ELLIPSIS = re.compile(r'\s*(?:…|\.\.\.|\[…\]|\[\.\.\.\])\s*')


def _greek(m):
    try:
        return unicodedata.lookup(('GREEK CAPITAL LETTER ' if m.group(1)[0].isupper() else 'GREEK SMALL LETTER ') + m.group(1).upper())
    except KeyError:
        return m.group(0)


def normalize(text):
    """Text as quotations are compared: no markup, one kind of quote and dash, lowercase, single spaces."""
    text = re.sub(r'!?\[([^\]\n]*)\]\([^)\n]*\)', r'\1', text)
    text = re.sub(r'\\([A-Za-z]+)', _greek, text)
    text = re.sub(r'[*`$\[\]\\\'"\u2018\u2019\u201c\u201d]|(?<!\w)_|_(?!\w)', '', text)  # markup, escapes and quote marks
    text = text.translate(str.maketrans({'\u2013': '-', '\u2014': '-', '\u2212': '-', '\u00a0': ' '}))
    return ' '.join(text.lower().split())


def found_in(quote, source):
    """Whether every part of the quotation appears in the source, in order."""
    variants = [normalize(source), normalize(re.sub(r'(\w)-\n\s*(\w)', r'\1\2', source))]
    parts = [normalize(p) for p in _ELLIPSIS.split(quote) if normalize(p)]
    for hay in variants:
        at = 0
        for part in parts:
            at = hay.find(part, at)
            if at < 0:
                break
            at += len(part)
        else:
            return True
    return False


def quotations(text):
    """[(line, quotation, citation target or None)] for each quotation in the narrative's prose:
    its citation is the first one after it, before the next quotation on the line."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    at = {}
    for c in citations.cites(text):
        at.setdefault(c.line, []).append((lines[c.line].find(f'[\\[{c.n}\\]]({c.target})'), c.target))
    out = []
    for i, line in enumerate(lines):
        if kinds[i] != 'text':
            continue
        found = list(QUOTE.finditer(mask_code_spans(line)))
        for k, m in enumerate(found):
            stop = found[k + 1].start() if k + 1 < len(found) else len(line)
            cite = next((target for pos, target in sorted(at.get(i, [])) if m.end() <= pos < stop), None)
            out.append((i + 1, m.group(1) or m.group(2) or m.group(3), cite))
    return out


def check(root, rel, text, max_words):
    out = []
    for line, quote, target in quotations(text):
        words = language.words(quote)
        if words > max_words:
            out.append(('error', 'QUOTE_TOO_LONG', line, f'a quotation of {words} words; quote at most {max_words} (max_quote_words), '
                                                         'or say it in your own words'))
        if target is None or words < MIN_WORDS:
            continue
        path, anchor = search.resolve(root, target, base=rel.rsplit('/', 1)[0])
        if path is None:
            continue  # a broken link: check_citation_targets reports it
        source = search.read_file(root, path)
        section = search.section(source, anchor) if anchor else source
        if section is not None and not found_in(quote, section):
            out.append(('error', 'QUOTE_NOT_FOUND', line, f'"{quote[:60]}" isn\'t in {target}; quote it word for word, or say it in your own words'))
    return out
