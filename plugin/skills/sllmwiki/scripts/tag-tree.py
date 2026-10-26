#!/usr/bin/env python3
"""tag-tree: answer questions about the tag tree (design doc §4.1).

  tag-tree.py tree [--brief]   every tag, indented under its parent, with its
                               description (--brief: names and counts only)
  tag-tree.py show <tag>       a tag: description, parent, ancestors, children,
                               adjacent tags, SMEs, sources and narratives

Options: --json for machine-readable output; --root <wiki>.
Exit code: 0, or 1 for an unknown tag, 2 for a usage error.
"""

import argparse
import sys

sys.dont_write_bytecode = True

from lib import tagtree  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps  # noqa: E402

cli = Cli('tag-tree.py', 'usage: tag-tree.py tree [--brief] | show <tag>')


def describe(tree, tag):
    e = tree.tags[tag]
    return {'tag': tag, 'description': e.get('description'), 'parent': e.get('parent'), 'ancestors': tree.ancestors(tag),
            'children': tree.children(tag), 'adjacent': tree.adjacent(tag), 'smes': e.get('smes') or [],
            'sources': tree.sources_of(tag), 'narratives': tree.narratives_of(tag)}


def main(argv):
    p = argparse.ArgumentParser(prog='tag-tree.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--root')
    p.add_argument('--json', action='store_true')
    sub = p.add_subparsers(dest='command', required=True)
    t = sub.add_parser('tree')
    t.add_argument('--brief', action='store_true')
    s = sub.add_parser('show')
    s.add_argument('tag')
    args = p.parse_args(argv)
    tree = tagtree.load(cli.wiki(args.root))

    if args.command == 'show':
        if args.tag not in tree.tags:
            cli.fail(f'no tag {args.tag}')
        d = describe(tree, args.tag)
        if args.json:
            print(dumps(d))
            return 0
        print(f'{d["tag"]}: {d["description"]}')
        for label, key in (('ancestors', 'ancestors'), ('children', 'children'), ('adjacent', 'adjacent'), ('sources', 'sources')):
            print(f'  {label}: {", ".join(d[key]) or "none"}')
        for role in ('primary', 'supporting'):
            print(f'  narratives ({role}): {", ".join(d["narratives"][role]) or "none"}')
        for sme in d['smes']:
            print(f'  sme: {sme}')
        return 0

    rows = [{'tag': tag, 'depth': depth, 'description': tree.tags[tag].get('description'), 'sources': len(tree.sources_of(tag)),
             'narratives': sum(len(v) for v in tree.narratives_of(tag).values())} for depth, tag in tree.walk()]
    if args.json:
        print(dumps(rows))
        return 0
    for r in rows:
        counts = f'({r["sources"]} sources, {r["narratives"]} narratives)'
        print(f'{"  " * r["depth"]}{r["tag"]} {counts}' + ('' if args.brief else f': {r["description"]}'))
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
