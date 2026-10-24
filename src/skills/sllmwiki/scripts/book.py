#!/usr/bin/env python3
"""book: the wiki as a book (docs/book_design.md).

  book.py stage OUT [--name N] [--version V] [--date YYYY-MM-DD] [--commit C]
      Writes the book as plain Markdown for Sphinx into the folder OUT, which
      must be empty or not exist yet: index.md (the cover, the front page and
      the contents), parts/<tag>.md, chapters/<slug>.md with their figures,
      and the appendices (sources, glossary, open questions). Also writes
      OUT/book.json: the parts, the chapter order, every anchor, every diagram
      and formula to render, and the problems found. The wiki is only read.
      --name defaults to the wiki's folder name, --version to "preview",
      --date to today and --commit to the current commit, if any.
      Problems: BOOK_LINK (a link or anchor the book can't resolve),
      BOOK_CYCLE (narratives built on each other in a cycle), BOOK_FIGURE (a
      figure that isn't there).

Options: --json, --root <wiki>.
Exit code: 0, 1 when there are problems (the book is still written), 2 on a
usage error.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

from lib import book, layout  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, write_text  # noqa: E402

cli = Cli('book.py', 'usage: book.py stage OUT [--name N] [--version V] [--date YYYY-MM-DD] [--commit C] [--json] [--root WIKI]')


def _commit(root):
    try:
        r = subprocess.run(['git', '-C', root, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, check=False)
    except OSError:  # pragma: no cover (no git)
        return ''
    return r.stdout.strip() if r.returncode == 0 else ''


def main(argv):
    p = argparse.ArgumentParser(prog='book.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=['stage'])
    p.add_argument('out')
    p.add_argument('--name')
    p.add_argument('--version', default='preview')
    p.add_argument('--date', default=datetime.date.today().isoformat())
    p.add_argument('--commit')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)
    out = os.path.abspath(args.out)
    if os.path.exists(out) and (not os.path.isdir(out) or os.listdir(out)):
        cli.usage(f'{args.out} must be an empty folder, or not exist yet')
    staged = book.stage(root, args.name or os.path.basename(root), args.version, args.date,
                        _commit(root) if args.commit is None else args.commit)
    for rel, text in staged.files.items():
        write_text(os.path.join(out, rel), text)
    for fig in staged.figures:
        dest = os.path.join(out, 'chapters', fig)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(root, layout.NARRATIVES, fig), dest)
    write_text(os.path.join(out, 'book.json'), json.dumps(staged.manifest, indent=1, ensure_ascii=False) + '\n')
    problems = staged.manifest['problems']
    if args.json:
        print(dumps({'out': out, 'chapters': len(staged.manifest['order']), 'renders': len(staged.manifest['renders']),
                     'problems': problems}))
    else:
        for pr in problems:
            print(f'{pr["code"]} {pr["where"]}: {pr["message"]}')
        print(f'{len(staged.manifest["order"])} chapters, {len(staged.manifest["renders"])} diagrams and formulas, '
              f'{len(problems)} problem{"s" if len(problems) != 1 else ""}: {out}')
    return 1 if problems else 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
