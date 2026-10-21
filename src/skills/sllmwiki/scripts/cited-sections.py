#!/usr/bin/env python3
"""cited-sections: each section a narrative cites, once, with the claims that cite it
(design doc §7.3), so lint reads those sections and not whole sources.

  cited-sections.py <narrative> [--claims-only] [--json] [--root <wiki>]

<narrative> is its slug or its path. For each cited target, in order of first
citation: the target, the claims citing it (the sentence before each citation,
with its line), then the section's text (a code source's lines, numbered).
--claims-only leaves the sections' text out. A target that doesn't resolve is
listed with the reason; wiki-check reports it too.

Exit code: 0, 1 when the narrative isn't found, 2 on a usage error.
"""

import argparse
import os
import re
import sys

sys.dont_write_bytecode = True

from lib import citations, layout, search  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, read_text  # noqa: E402

cli = Cli('cited-sections.py', 'usage: cited-sections.py <narrative> [--claims-only] [--json]')
_LINKS = re.compile(r'\[\\\[[0-9]+\\\]\]\([^)\s]*\)')
_SENTENCE_END = re.compile(r'(?<=[.!?:;])[*_]*\s+(?=\S)')


def claim(line, start):
    """The sentence a citation at line[start] backs: the text before it since the last sentence end."""
    before = _LINKS.sub('', line[:start]).strip()
    before = re.sub(r'^\s*(?:[-*+]|\d+\.|\|)\s*', '', before)
    parts = [p for p in _SENTENCE_END.split(before) if p.strip()]
    return parts[-1].strip(' |*') if parts else ''


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
    p = argparse.ArgumentParser(prog='cited-sections.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
    out = []
    for target, claims in collect(text):
        path, anchor = search.resolve(root, target, base=os.path.dirname(rel))
        section, problem = None, None
        if path is None:
            problem = 'no such file'
        elif not anchor:
            problem = 'cites the whole file, not a section'
        else:
            section = search.section(search.read_file(root, path), anchor)
            problem = None if section is not None else f'{path} has no section #{anchor}'
        out.append({'target': target, 'file': path, 'anchor': anchor, 'claims': [{'line': ln, 'n': n, 'claim': c} for ln, n, c in claims],
                    'problem': problem, 'text': None if args.claims_only else section})
    if args.json:
        print(dumps({'narrative': rel, 'cited': out}))
        return 0
    for item in out:
        print(f'## {item["target"]}' + (f'  ({item["problem"]})' if item['problem'] else ''))
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


if __name__ == '__main__':  # pragma: no cover
    entry(main)
