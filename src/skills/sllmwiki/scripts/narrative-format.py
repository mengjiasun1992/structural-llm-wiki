#!/usr/bin/env python3
"""narrative-format: check narratives against their template, and the rules every
narrative shares (design doc §4.5, §4.8, §4.10).

  narrative-format.py [<narrative.md> ...] [--fix-numbering] [--fix-style] [--json]
      Checks the given narratives, or every one in sllmwiki/narratives/:
        the # title; the template named in Metadata; the template's sections, in
        order, and its diagrams; heading numbers; the Abstract's word range and
        the body's budget; citations (numbered in order, listed, pointing at an
        existing section of a saved source); the markers; leftover <placeholders>;
        and markdown every renderer reads alike, links included.
      --fix-numbering renumbers the headings; --fix-style writes the renderer
      escapes. finish-narrative.py does both, and more.
  narrative-format.py --templates     the templates this wiki offers, with use_when and budgets
  narrative-format.py --skeleton NAME the skeleton a new narrative starts from

Options: --root <wiki>. Exit code: 0 with no errors (warnings are printed),
1 with errors, 2 on a usage error.
"""

import argparse
import glob
import os
import sys

sys.dont_write_bytecode = True

from lib import compat, config, layout, numbering, templates  # noqa: E402
from lib.narrativecheck import check  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, read_text, write_text  # noqa: E402

cli = Cli('narrative-format.py', 'usage: narrative-format.py [<narrative.md> ...] [--fix-numbering] [--fix-style] | --templates | --skeleton NAME')
def main(argv):
    p = argparse.ArgumentParser(prog='narrative-format.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('files', nargs='*')
    p.add_argument('--fix-numbering', action='store_true')
    p.add_argument('--fix-style', action='store_true')
    p.add_argument('--templates', action='store_true')
    p.add_argument('--skeleton', metavar='NAME')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)
    offered, problems = templates.available(root)

    if args.templates:
        rows = [{'name': t.name, 'source': t.source, 'description': t.description, 'use_when': t.use_when,
                 'max_words': t.max_words, 'abstract_words': t.abstract_words} for t in offered.values()]
        if args.json:
            print(dumps({'templates': rows, 'problems': problems}))
        else:
            for r in rows:
                print(f'{r["name"]} ({r["source"]}, body up to {r["max_words"]} words): {r["description"]}. Use for {r["use_when"]}')
            for prob in problems:
                print(f'problem: {prob}')
        return 1 if problems else 0
    if args.skeleton:
        if args.skeleton not in offered:
            cli.fail(f'no template {args.skeleton}; there are {", ".join(sorted(offered))}')
        print(offered[args.skeleton].skeleton(), end='')
        return 0

    settings = config.get(root).settings
    files = args.files or sorted(glob.glob(os.path.join(root, layout.NARRATIVES, '*.md')))
    results, errors = [], 0
    for f in files:
        path = f if os.path.isabs(f) else os.path.join(os.getcwd(), f)
        if not os.path.isfile(path):
            cli.fail(f'no such file: {f}')
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(root)).replace(os.sep, '/')  # real paths: /var is /private/var on macOS
        text = read_text(path)
        fixed = text
        if args.fix_numbering:
            fixed = numbering.renumber(fixed)[0]
        if args.fix_style:
            fixed = compat.escape(fixed)[0]
        if fixed != text:
            write_text(path, fixed)
            print(f'fixed {rel}')
        for sev, code, line, msg in check(root, rel, fixed, settings, offered):
            results.append({'file': rel, 'line': line, 'severity': sev, 'code': code, 'message': msg})
            errors += sev == 'error'
    for prob in problems:
        results.append({'file': layout.TEMPLATES, 'line': 1, 'severity': 'error', 'code': 'TEMPLATE_INVALID', 'message': prob})
        errors += 1
    if args.json:
        print(dumps({'errors': errors, 'warnings': len(results) - errors, 'findings': results}))
    else:
        for r in results:
            print(f'{r["severity"]:<8} {r["code"]:<20} {r["file"]}:{r["line"]}: {r["message"]}')
        print(f'narrative-format: {errors} error(s), {len(results) - errors} warning(s) in {len(files)} narrative(s)')
    return 1 if errors else 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
