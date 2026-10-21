#!/usr/bin/env python3
"""manifest: write tags.yaml and the manifests, one checked entry at a time,
so they're never edited by hand (design doc §4.2-§4.4).

  manifest.py add-tag <tag> --description TEXT [--parent TAG]
  manifest.py put-tag <tag> [--description TEXT] [--smes "@a: why" "@b: why" | --no-smes]
  manifest.py put-source <slug> [--kind link] [--url URL] [--published DATE] [--license ID]
                         [--license-url URL] [--tags a,b] [--abstract TEXT]
      Records a link, or changes the fields of an existing source; saved copies
      come from fetch-source.py.
  manifest.py set-abstract <slug> --abstract TEXT
      The agent's abstract for a source, replacing a draft.
  manifest.py put-narrative <slug> --template NAME --primary a,b [--supporting c] [--read s1,s2]
      Usually through finish-narrative.py, which also pins the sources read.
  manifest.py remove <tags|sources|narratives> <key>

Every command takes --root <wiki> (default: the repository around the working
directory). Exit code: 0 done, 1 refused (the reason is printed), 2 usage error.
"""

import argparse
import sys

sys.dont_write_bytecode = True

from lib import config, manifest  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import today  # noqa: E402

cli = Cli('manifest.py', 'usage: manifest.py <command> ...; see --help')


def tags_arg(value):
    return [t.strip() for t in value.split(',') if t.strip()]


def parser():
    p = argparse.ArgumentParser(prog='manifest.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--root')
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('add-tag')
    a.add_argument('tag')
    a.add_argument('--description', required=True)
    a.add_argument('--parent')
    t = sub.add_parser('put-tag')
    t.add_argument('tag')
    t.add_argument('--description')
    g = t.add_mutually_exclusive_group()
    g.add_argument('--smes', nargs='+')
    g.add_argument('--no-smes', action='store_true')
    s = sub.add_parser('put-source')
    s.add_argument('slug')
    s.add_argument('--kind', choices=['link'])
    for opt in ('--url', '--published', '--license', '--license-url', '--abstract'):
        s.add_argument(opt)
    s.add_argument('--tags', type=tags_arg)
    b = sub.add_parser('set-abstract')
    b.add_argument('slug')
    b.add_argument('--abstract', required=True)
    n = sub.add_parser('put-narrative')
    n.add_argument('slug')
    n.add_argument('--template', required=True)
    n.add_argument('--primary', type=tags_arg, required=True)
    n.add_argument('--supporting', type=tags_arg, default=[])
    n.add_argument('--read', type=tags_arg, default=[])
    r = sub.add_parser('remove')
    r.add_argument('kind', choices=['tags', 'sources', 'narratives'])
    r.add_argument('key')
    return p


def main(argv):
    args = parser().parse_args(argv)
    root = cli.wiki(args.root)
    try:
        config.load(root)
    except config.ConfigError as e:
        cli.fail('Config.toml is invalid, fix it first: ' + '; '.join(e.problems))
    try:
        if args.command == 'add-tag':
            manifest.add_tag(root, args.tag, args.description, args.parent)
            print(f'added tag {args.tag}')
        elif args.command == 'put-tag':
            manifest.put_tag(root, args.tag, args.description, [] if args.no_smes else args.smes)
            print(f'updated tag {args.tag}')
        elif args.command == 'put-source':
            new = args.slug not in manifest.load(root, 'sources')
            manifest.put_source(root, args.slug, kind=args.kind, url=args.url, published=args.published, license=args.license,
                                license_url=args.license_url, tags=args.tags, abstract=args.abstract,
                                ingested=today() if new else None)
            print(f'{"recorded" if new else "updated"} source {args.slug}')
        elif args.command == 'set-abstract':
            manifest.set_abstract(root, args.slug, args.abstract)
            print(f'set the abstract of {args.slug}')
        elif args.command == 'put-narrative':
            manifest.put_narrative(root, args.slug, args.template, args.primary, args.supporting, args.read)
            print(f'recorded narrative {args.slug}')
        else:
            manifest.remove(root, args.kind, args.key)
            print(f'removed {args.key} from {args.kind}')
    except manifest.ManifestError as e:
        cli.fail(str(e))
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
