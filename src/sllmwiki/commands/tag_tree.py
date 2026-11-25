"""tag-tree: answer questions about the tag tree (design doc §4.1).

  sllmwiki tag-tree tree [--brief]   every tag, indented under its parent, with its
                               description (--brief: names and counts only)
  sllmwiki tag-tree show <tag>       a tag: description, parent, ancestors, children,
                               adjacent tags, SMEs, sources and narratives
  sllmwiki tag-tree review [--new a,b]
                               the tree, then each tag a reader may not expect
                               where it is (exit 1 when there's one):
      TAG_NO_PRIMARY      a leaf no narrative has as a primary tag
      TAG_OTHER_ROOT      a tag most of whose narratives have their other primary tags
                          under one other root
      TAG_BUILDS_ON_ROOT  a tag most of whose subtree's narratives link to, build on
                          or need narratives under one other root: it may be a kind
                          of that root (reported on the highest such tag)
      TAG_RETAG           with --new, the tags a run added: each narrative not filed
                          under one that links to, builds on or needs its narratives,
                          or names it: it may need the tag, at least as supporting

Options: --json for machine-readable output; --root <wiki>.
Exit code: 0, or 1 for an unknown tag or a review finding, 2 for a usage error.
"""

import argparse

from sllmwiki.lib import tagtree
from sllmwiki.lib.layout import Cli
from sllmwiki.lib.util import comma_list, dumps

cli = Cli('sllmwiki tag-tree', 'usage: sllmwiki tag-tree tree [--brief] | show <tag> | review')


def describe(tree, tag):
    e = tree.tags[tag]
    return {'tag': tag, 'description': e.get('description'), 'parent': e.get('parent'), 'ancestors': tree.ancestors(tag),
            'children': tree.children(tag), 'adjacent': tree.adjacent(tag), 'smes': e.get('smes') or [],
            'sources': tree.sources_of(tag), 'narratives': tree.narratives_of(tag)}


def main(argv):
    p = argparse.ArgumentParser(prog='sllmwiki tag-tree', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--root')
    p.add_argument('--json', action='store_true')
    sub = p.add_subparsers(dest='command', required=True)
    t = sub.add_parser('tree')
    t.add_argument('--brief', action='store_true')
    s = sub.add_parser('show')
    s.add_argument('tag')
    r = sub.add_parser('review')
    r.add_argument('--new', type=comma_list, default=[])
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

    if args.command == 'review':
        unknown = [t for t in args.new if t not in tree.tags]
        if unknown:
            cli.usage(f'--new names no tag {", ".join(unknown)}')
        ties = tagtree.narrative_ties(cli.wiki(args.root), tree.narratives)
        findings = [{'code': c, 'tag': t, 'message': m} for c, t, m in tree.review(ties, args.new)]
        if args.json:
            print(dumps({'tree': [{'tag': t, 'depth': d, 'parent': tree.parent(t)} for d, t in tree.walk()], 'findings': findings}))
            return 1 if findings else 0
        for depth, tag in tree.walk():
            on = tree.narratives_of(tag)
            print(f'{"  " * depth}{tag} ({len(on["primary"])} primary, {len(on["supporting"])} supporting): {tree.tags[tag].get("description")}')
        print()
        for f in findings:
            print(f'{f["code"]:<16} {f["message"]}')
        print(f'tag-tree review: {len(findings)} finding(s)')
        return 1 if findings else 0

    rows = [{'tag': tag, 'depth': depth, 'description': tree.tags[tag].get('description'), 'sources': len(tree.sources_of(tag)),
             'narratives': sum(len(v) for v in tree.narratives_of(tag).values())} for depth, tag in tree.walk()]
    if args.json:
        print(dumps(rows))
        return 0
    for r in rows:
        counts = f'({r["sources"]} sources, {r["narratives"]} narratives)'
        print(f'{"  " * r["depth"]}{r["tag"]} {counts}' + ('' if args.brief else f': {r["description"]}'))
    return 0
