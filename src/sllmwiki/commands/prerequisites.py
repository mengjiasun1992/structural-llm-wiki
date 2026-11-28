"""prerequisites: which narratives a reader reads first (design doc §4.5.2).

  sllmwiki prerequisites propose [<slug> ...] [--json] [--root <wiki>]
  sllmwiki prerequisites migrate [--json] [--root <wiki>]

propose lists, for each narrative (or those named), the other narratives it may
need first, with the evidence: it builds on one (built_on), links to it, or uses
a term the other defines in its Terminology or Glossary and it doesn't. A
candidate marked "cycle" needs this one first already, and "indirect" is needed by
one of its prerequisites already: neither is a direct prerequisite. It also lists
each recorded prerequisite the narrative neither links to nor takes a term from,
for lint to check. The evidence is a list to judge, not an answer: record the
narratives whose concepts it uses without explaining them, with sllmwiki
finish-narrative <slug> --prerequisite <slug> ...

migrate brings a wiki's narratives to prerequisites, once: it moves each
narrative's hand-written "Where to go next" section into its Appendix, where the
generated Before you read and Where to go next go (keeping the pins on it, since
nothing a reader reads changed), lists each passage of a body that states a
reading order (narrative-format's READING_ORDER_IN_BODY: record it as
prerequisites, then remove it), then prints propose's list for every narrative
that records no prerequisites yet.

Exit code: 0, or 2 on a usage error or a narrative that isn't there.
"""

import argparse
import os

from sllmwiki.lib import config, language, layout, manifest, prerequisites
from sllmwiki.lib.layout import Cli
from sllmwiki.lib.util import dumps, read_text, write_text

cli = Cli('sllmwiki prerequisites', 'usage: sllmwiki prerequisites propose [<slug> ...] [--json] | migrate [--json]')


def _evidence(e):
    parts = (['built on it'] if e['built_on'] else []) + ([f'links to it {e["links"]} time(s)'] if e['links'] else []) \
        + ([f'uses its terms: {", ".join(e["terms"])}'] if e['terms'] else [])
    flags = [f for f in ('cycle', 'indirect') if e[f]]
    return '; '.join(parts) + (f' ({", ".join(flags)})' if flags else '')


def _print(found):
    for slug, f in found.items():
        print(f'{slug} (prerequisites: {", ".join(f["prerequisites"]) or "none"})')
        for other, e in f['candidates'].items():
            print(f'  {other}: {_evidence(e)}')
        for other in f['unused']:
            print(f'  unused? {other}: no link to it and none of its terms')


def migrate(root):
    """([narratives whose Where to go next moved], {slug: [(line, passage)]} stating a reading order): moved,
    written, and the pins on them kept."""
    default = config.get(root).settings['language']
    before, moved, stated = {}, [], {}
    for slug in sorted(manifest.load(root, 'narratives')):
        path = os.path.join(root, layout.NARRATIVES, f'{slug}.md')
        if not os.path.isfile(path):
            continue
        text = read_text(path)
        new, did = prerequisites.move_next(text, default)
        if did:
            before[slug] = text
            write_text(path, new)
            moved.append(slug)
        found = prerequisites.stated_order(new, language.for_narrative(new, default)[0])
        if found:
            stated[slug] = found
    prerequisites.sync(root, write=True)
    if before:
        manifest.repin(root, before)
    return moved, stated


def main(argv):
    p = argparse.ArgumentParser(prog='sllmwiki prerequisites', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('action', choices=['propose', 'migrate'])
    p.add_argument('slugs', nargs='*')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)
    if args.action == 'migrate' and args.slugs:
        cli.usage('migrate takes every narrative; name none')
    moved, stated = migrate(root) if args.action == 'migrate' else (None, None)
    try:
        found = prerequisites.propose(root, args.slugs or None)
    except ValueError as e:
        cli.usage(str(e))
    if moved is not None:
        found = {s: f for s, f in found.items() if not f['prerequisites']}
    if args.json:
        print(dumps({'moved': moved, 'reading_order': {s: [{'line': i, 'text': t} for i, t in f] for s, f in stated.items()},
                     'narratives': found} if moved is not None else {'narratives': found}))
        return 0
    if moved is not None:
        print(f'moved Where to go next into the Appendix in {len(moved)} narrative(s)' + (f': {", ".join(moved)}' if moved else ''))
        if stated:
            print('reading orders stated in a body (record them as prerequisites, then remove them):')
            for slug, f in stated.items():
                for i, t in f:
                    print(f'  {slug}:{i}: "{t}"')
        print('proposed prerequisites, for the narratives that record none:' if found else 'every narrative records its prerequisites')
    _print(found)
    return 0
