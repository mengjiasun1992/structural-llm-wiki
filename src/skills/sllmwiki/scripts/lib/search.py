"""Finding what to read (design doc §6): BM25 over short fields (tag names and
descriptions, narrative questions and abstracts, source abstracts), and one
section of a file, so an answer reads the smallest thing that answers it.

BM25 matches words, not meanings: callers pass keywords and synonyms.
"""

import math
import os
import re

from . import language, layout, manifest, metadata, numbering, plaintext
from .util import read_bytes, read_text, split_footer

STOP = set('a an and are as at be but by can do does for from how i in is it its of on or that the their this to was what when '
           'where which who why will with you your'.split())
K1, B = 1.5, 0.75


_CJK_RUN = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+')


def tokens(text):
    """The words to match on: lowercase letters and digits, and each pair of CJK characters side by side
    (Chinese and Japanese put no spaces between words)."""
    text = (text or '').lower()
    out = [w for w in re.findall(r'[a-z0-9]+', text) if w not in STOP]
    for run in _CJK_RUN.findall(text):
        out += [run] if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)]
    return out


def bm25(query, docs):
    """[(score, key)] for {key: text}, best first, only those that match."""
    q = set(tokens(query))
    toks = {k: tokens(v) for k, v in docs.items()}
    n = len(toks) or 1
    avg = sum(len(t) for t in toks.values()) / n or 1
    df = {w: sum(1 for t in toks.values() if w in t) for w in q}
    out = []
    for k, t in toks.items():
        score = 0.0
        for w in q:
            f = t.count(w)
            if f:
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                score += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * len(t) / avg))
        if score > 0:
            out.append((round(score, 3), k))
    return sorted(out, key=lambda x: (-x[0], x[1]))


def narratives(root):
    """{slug: {question, abstract, path, version, tags}} read from the narrative files and their manifest entries."""
    recorded = manifest.load(root, 'narratives')
    out = {}
    for slug, entry in recorded.items():
        rel = f'{layout.NARRATIVES}/{slug}.md'
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        text = read_text(path)
        out[slug] = {'question': metadata.title(text), 'abstract': metadata.abstract(text), 'path': rel,
                     'version': metadata.read(text)['version'], 'tags': entry.get('tags', {})}
    return out


def find_tags(root, query, limit=5):
    tags = manifest.load(root, 'tags')
    ranked = bm25(query, {t: f'{t.replace("-", " ")} {e.get("description", "")}' for t, e in tags.items()})
    return [{'tag': t, 'score': s, 'description': tags[t].get('description')} for s, t in ranked[:limit]]


def find_narratives(root, query, limit=5):
    found = narratives(root)
    ranked = bm25(query, {k: f'{v["question"]} {v["question"]} {v["abstract"]}' for k, v in found.items()})
    return [dict(found[k], slug=k, score=s) for s, k in ranked[:limit]]


def find_sources(root, query, tags=None, limit=5):
    sources = manifest.load(root, 'sources')
    pool = {k: v for k, v in sources.items() if not tags or set(tags) & set(v.get('tags') or [])}
    ranked = bm25(query, {k: v.get('abstract', '') for k, v in pool.items()})
    return [{'slug': k, 'score': s, 'kind': pool[k].get('kind'), 'abstract': pool[k].get('abstract'), 'abstract_draft': bool(pool[k].get('abstract_draft')),
             'path': layout.in_content(pool[k]['file']) if pool[k].get('file') else None, 'url': pool[k].get('url')} for s, k in ranked[:limit]]


def resolve(root, link, base=layout.NARRATIVES):
    """(repository-relative path, anchor) for a link as a citation writes it
    (../sources/x.md#a, relative to base), as a path from the root, or as a slug#anchor."""
    path, _, anchor = link.partition('#')
    candidates = [os.path.normpath(os.path.join(base, path)).replace(os.sep, '/'), path,
                  f'{layout.SOURCES}/{path}.md', f'{layout.NARRATIVES}/{path}.md']
    rel = next((c for c in candidates if c and not c.startswith('..') and os.path.isfile(os.path.join(root, c))), None)
    return rel, anchor


def read_file(root, rel):
    """A file's text; a saved source without its footer, which isn't the source's content."""
    if rel.startswith(layout.SOURCES + '/'):
        return split_footer(read_bytes(os.path.join(root, rel)))[0].decode('utf-8', 'replace')
    return read_text(os.path.join(root, rel))


def outline(text):
    """[{level, title, anchor, words}] of a file's headings, each with its section's word count."""
    lines = text.split('\n')
    heads = numbering.headings(text)
    by_line = {h.line: a for a, h in numbering.anchors(text).items()}
    out = []
    for i, h in enumerate(heads):
        end = next((g.line for g in heads[i + 1:] if g.level <= h.level), len(lines))
        out.append({'level': h.level, 'title': h.text, 'anchor': by_line[h.line],
                    'words': language.words('\n'.join(lines[h.line + 1:end]))})
    return out


def section(text, anchor):
    """The section's text, its heading included, or a code source's lines (#L10-L20), numbered; None when there is no such section."""
    code = plaintext.lines(text, anchor)
    if code is not None:
        start = int(plaintext.LINES.match(anchor).group('start'))
        return '\n'.join(f'{start + i}: {line}' for i, line in enumerate(code)) + '\n'
    span = numbering.section(text, anchor)
    return '\n'.join(text.split('\n')[span[0]:span[1]]).rstrip('\n') + '\n' if span else None
