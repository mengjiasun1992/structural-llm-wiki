"""cited-sections: each section a narrative cites, once, with the claims that cite it
(design doc §7.3), so lint reads those sections and not whole sources.

  sllmwiki cited-sections <narrative> [--claims-only] [--json] [--root <wiki>]

<narrative> is its slug or its path. For each cited target, in order of first
citation: the target, the claims citing it (the sentence before each citation,
with its line), then the section's text (a code source's lines, numbered).
--claims-only leaves the sections' text out. A target that doesn't resolve is
listed with the reason (wiki-check reports it too), and so is one that names the
whole file or the page's title (its top heading), which lint reports. A section
inside another cited one is printed once, in the larger; links print as their
text, without their URLs.

Exit code: 0, 1 when the narrative isn't found, 2 on a usage error.
"""

import argparse
import os
import re

from sllmwiki.lib import citations, layout, numbering, plaintext, search
from sllmwiki.lib.layout import Cli
from sllmwiki.lib.util import dumps, read_text

cli = Cli('sllmwiki cited-sections', 'usage: sllmwiki cited-sections <narrative> [--claims-only] [--json]')
_LINKS = re.compile(r'\[\\\[[0-9]+\\\]\]\([^)\s]*\)')
_MD_LINK = re.compile(r'\[([^\]\n]*)\]\([^)\s]*(?:\s+"[^"]*")?\)')  # [text](url): an agent reading a section needs the text
_SENTENCE_END = re.compile(r'(?<=[.!?:;])[*_]*\s+(?=\S)|(?<=[。！？；：])[*_]*\s*(?=\S)')


def claim(line, start):
    """The sentence a citation at line[start] backs: the text before it since the last sentence end."""
    before = _LINKS.sub('', line[:start]).strip()
    before = re.sub(r'^\s*(?:[-*+]|\d+\.|\|)\s*', '', before)
    parts = [p for p in _SENTENCE_END.split(before) if p.strip()]
    return parts[-1].strip(' |*,') if parts else ''


def collect(text):
    """[(target, [(line, n, claim)])] in order of first citation."""
    lines = text.split('\n')
    found, last = {}, {}
    for c in citations.cites(text):
        line = lines[c.line]
        start = line.find(f'[\\[{c.n}\\]]({c.target})')
        said = claim(line, start) or last.get(c.line, '')  # a second citation right after the first backs the same claim
        last[c.line] = said
        found.setdefault(c.target, []).append((c.line + 1, c.n, said))
    return list(found.items())


def main(argv):
    p = argparse.ArgumentParser(prog='sllmwiki cited-sections', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('narrative')
    p.add_argument('--claims-only', action='store_true')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)
    rel, _ = search.resolve(root, args.narrative)
    if rel is None or not rel.startswith(layout.NARRATIVES + '/'):
        cli.fail(f'no narrative {args.narrative}')
    text = read_text(os.path.join(root, rel))
    files, spans, out = {}, {}, []
    for target, claims in collect(text):
        path, anchor = search.resolve(root, target, base=os.path.dirname(rel))
        section, problem = None, None
        if path is None:
            problem = 'no such file'
        elif not anchor:
            problem = 'cites the whole file, not a section'
        else:
            body = files.setdefault(path, search.read_file(root, path))  # each source read once
            span = None if plaintext.LINES.match(anchor) else numbering.section(body, anchor)
            heads = numbering.headings(body)
            if span and heads and heads[0].line == span[0] and heads[0].level == 1 and span[1] >= len(body.split('\n')):
                problem = 'cites the whole page (its title), not a section'
            else:
                section = search.section(body, anchor)
                problem = None if section is not None else f'{path} has no section #{anchor}'
                if span and section is not None:
                    spans.setdefault(path, []).append((span, target))
        out.append({'target': target, 'file': path, 'anchor': anchor, 'claims': [{'line': ln, 'n': n, 'claim': c} for ln, n, c in claims],
                    'problem': problem, 'text': None if args.claims_only else section})
    for item in out:  # a section inside a larger cited one: its text is printed there
        mine = next((sp for sp, tg in spans.get(item['file'], ()) if tg == item['target']), None)
        outer = next((tg for sp, tg in spans.get(item['file'], ()) if mine and tg != item['target']
                      and sp[0] <= mine[0] and mine[1] <= sp[1] and sp != mine), None)
        if outer:
            item['inside'] = outer
            item['text'] = None
        elif item['text'] and not plaintext.LINES.match(item['anchor'] or ''):
            item['text'] = _MD_LINK.sub(r'\1', item['text'])
    if args.json:
        print(dumps({'narrative': rel, 'cited': out}))
        return 0
    for item in out:
        note = item['problem'] or (f'inside {item["inside"]}, printed there' if item.get('inside') else '')
        print(f'## {item["target"]}' + (f'  ({note})' if note else ''))
        print()
        for c in item['claims']:
            print(f'- line {c["line"]} [{c["n"]}]: {c["claim"]}')
        if item['text']:
            print()
            print(item['text'].rstrip('\n'))
        print()
    if not out:
        print(f'{rel} cites nothing')
    return 0
