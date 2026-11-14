"""search: find what to read, and read only that (design doc §6.1).

  sllmwiki search context "<keywords>"         the wiki's audience profile, when it has one, to write the
                                          answer for; the matching tags, each with its SMEs; and the top
                                          narratives, each with its abstract and the sources it
                                          read that have changed since: query's first tier, in one call
  sllmwiki search narratives "<keywords>"      the top narratives: question, abstract, path
  sllmwiki search sources "<keywords>" [--tags a,b]
                                          the top sources by abstract (only those tags')
  sllmwiki search outline <file or slug>       a file's headings, anchors and word counts
  sllmwiki search section "<link>"             one section: pass a citation link as is
                                          (../sources/x.md#section), a path#anchor or a slug#anchor

Pass keywords with synonyms: ranking matches words, not meanings.
Options: --limit N (default 5), --json, --root <wiki>.
Exit code: 0, 1 when nothing is found for outline or section, 2 on a usage error.
"""

import argparse
import sys

from sllmwiki.lib import audience, search
from sllmwiki.lib.layout import Cli
from sllmwiki.lib.util import comma_list, dumps

cli = Cli('sllmwiki search', 'usage: sllmwiki search context|narratives|sources "<keywords>" | outline <file> | section "<link>"')


def show_narratives(found):
    for n in found:
        stale = f'\n\nBuilt on an older version of {", ".join(n["changed"])}: say so with the answer.' if n.get('changed') else ''
        print(f'## {n["question"]}  ({n["path"]}, version {n["version"]}, score {n["score"]})\n\n{n["abstract"]}{stale}\n')


def main(argv):
    p = argparse.ArgumentParser(prog='sllmwiki search', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=['context', 'narratives', 'sources', 'outline', 'section'])
    p.add_argument('what')
    p.add_argument('--tags', type=comma_list)
    p.add_argument('--limit', type=int, default=5)
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)

    if args.command == 'context':
        profile = audience.read(root)
        for prob in audience.problems(root):
            print(f'search: {prob}', file=sys.stderr)
        result = {'audience': profile, 'tags': search.find_tags(root, args.what, args.limit),
                  'narratives': search.find_narratives(root, args.what, args.limit)}
        if args.json:
            print(dumps(result))
            return 0
        if profile:
            print(f'Write the answer for this wiki\'s audience ({audience.path(root)}), before the skill and its guides:\n\n{profile}\n')
        print('Tags:' + ('' if result['tags'] else ' none match'))
        for t in result['tags']:
            print(f'- {t["tag"]}: {t["description"]}' + ''.join(f'\n  - SME {s}' for s in t['smes']))
        print()
        show_narratives(result['narratives']) if result['narratives'] else print('No narrative matches.')
        return 0
    if args.command == 'narratives':
        found = search.find_narratives(root, args.what, args.limit)
        print(dumps(found)) if args.json else show_narratives(found) if found else print('No narrative matches.')
        return 0
    if args.command == 'sources':
        found = search.find_sources(root, args.what, args.tags, args.limit)
        if args.json:
            print(dumps(found))
        for s in [] if args.json else found:
            draft = ' (draft abstract)' if s['abstract_draft'] else ''
            print(f'- {s["slug"]} [{s["kind"]}] {s["path"] or s["url"]}{draft}: {s["abstract"]}')
        if not found and not args.json:
            print('No source matches.')
        return 0

    rel, anchor = search.resolve(root, args.what)
    if rel is None:
        cli.fail(f'no such file: {args.what.partition("#")[0]}')
    text = search.read_file(root, rel)
    if args.command == 'outline':
        rows = search.outline(text)
        if args.json:
            print(dumps({'file': rel, 'headings': rows}))
        for r in [] if args.json else rows:
            print(f'{"  " * (r["level"] - 1)}{r["title"]}  #{r["anchor"]}  ({r["words"]} words)')
        return 0
    found = search.section(text, anchor) if anchor else None
    if found is None:
        cli.fail(f'{rel} has no section #{anchor}; see sllmwiki search outline {rel}' if anchor else 'section needs a #anchor; see sllmwiki search outline')
    print(dumps({'file': rel, 'anchor': anchor, 'text': found}) if args.json else f'<!-- {rel}#{anchor} -->\n{found}', end='' if not args.json else '\n')
    return 0
